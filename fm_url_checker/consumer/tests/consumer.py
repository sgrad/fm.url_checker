import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
import re
from aio_pika import IncomingMessage
from aiohttp import ClientConnectorError, ClientOSError
from flexmock import flexmock

from fm_url_checker.consumer import url_check
from fm_url_checker.consumer.models import Job, ValidationError, JobResult

UUID_REX = re.compile(r"[0-9a-f]{32}")


class FakeAiohttpResponse:
    def __init__(self, status: int = 200, body: str = "body"):
        self.status = status
        self.body = body

    async def text(self):
        return self.body


class FakeAiohttpSession:
    def __init__(self, status: int = 200, body: str = "body", exception: Exception = None):
        self.url = None
        self.response = FakeAiohttpResponse(status=status, body=body)
        self.exception = exception

        self.extra_args = None
        self.extra_kwargs = None

    @asynccontextmanager
    async def get(self, url, *args, **kwargs):
        if self.exception:
            raise self.exception
        self.url = url
        self.extra_args = args
        self.extra_kwargs = kwargs
        yield self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        pass


class FakeIncomingMessage(IncomingMessage):
    # noinspection PyMissingConstructor
    def __init__(self,
                 content_encoding: str = "utf8",
                 headers: dict = None,
                 job_id: str = None,
                 body: bytes = None,
                 body_dict: dict = None,
                 url: str = None):
        self.content_encoding = content_encoding
        self.headers = headers or {"job_id": job_id or uuid4().hex}
        if body is not None:
            self.body = body
        else:
            self.body = json.dumps(body_dict or {"url": url or "http://www.google.com"}).encode("utf8")

        self.ack_called = False
        self.nack_called = False
        self.reject_called = False
        self.reject_requeue = None

    def info(self):
        return {}

    def ack(self, *args, **kwargs):
        self.ack_called = True

    def nack(self, *args, **kwargs):
        self.nack_called = True

    def reject(self, requeue: bool = False, *args, **kwargs):
        self.reject_called = True
        self.reject_requeue = requeue

    def __setattr__(self, key, value):
        """ disable the custom functionality in the pika incoming message class """
        object.__setattr__(self, key, value)


@pytest.mark.consumer
class TestValidation:
    def test_valid_job(self):
        job_id = uuid4().hex
        url = "http://www.google.com"
        message = FakeIncomingMessage(job_id=job_id, url=url)

        job: Job = url_check._validate_message(message)

        assert job, "no job returned"
        assert job.id == job_id, "wrong job id returned"
        assert job.url == url, "wrong url returned"

    def test_invalid_encoding(self):
        with pytest.raises(ValidationError, match=".*wrong encoding.*"):
            url_check._validate_message(FakeIncomingMessage(content_encoding="bad_mojo"))

    def test_invalid_job_id(self):
        # missing
        with pytest.raises(ValidationError, match=".*malformed id.*"):
            url_check._validate_message(FakeIncomingMessage(headers={"not_job_id": "val"}))

        # empty job_id type
        with pytest.raises(ValidationError, match=".*malformed id.*"):
            url_check._validate_message(FakeIncomingMessage(headers={"job_id": ""}))

        # bad job_id type
        with pytest.raises(ValidationError, match=".*malformed id.*"):
            url_check._validate_message(FakeIncomingMessage(headers={"job_id": 123}))

        # bad job_id uuid
        with pytest.raises(ValidationError, match=".*malformed id.*"):
            url_check._validate_message(FakeIncomingMessage(headers={"job_id": "123456789012345678901234567890aX"}))

    def test_invalid_body(self):
        # missing body
        with pytest.raises(ValidationError, match=".*malformed job body.*JSONDecodeError.*"):
            url_check._validate_message(FakeIncomingMessage(body=b""))

        # not json body
        with pytest.raises(ValidationError, match=".*malformed job body.*JSONDecodeError.*"):
            url_check._validate_message(FakeIncomingMessage(body=b"{\"a\":}"))

        # not unicode body
        with pytest.raises(ValidationError, match=".*malformed job body.*UnicodeDecodeError.*"):
            url_check._validate_message(FakeIncomingMessage(body=b"abc\xdd"))

        # missing url
        with pytest.raises(ValidationError, match=".*malformed job body.*KeyError.*"):
            url_check._validate_message(FakeIncomingMessage(body_dict={"not_url": "something"}))


@pytest.mark.consumer
@pytest.mark.asyncio
class TestProcessJob:
    async def test_ok(self):
        job_id = uuid4().hex
        job = Job(id=job_id, url="url")
        fake_session = FakeAiohttpSession(body="body")
        (flexmock(url_check)
         .should_receive("ClientSession")
         .and_return(fake_session))
        result = await url_check._process_job(job=job)
        assert result.job == job, "wrong job returned"
        assert result.status == 200, "wrong status returned"
        assert result.size == 4, "wrong size returned"

    async def test_client_error(self):
        job_id = uuid4().hex
        job = Job(id=job_id, url="url")
        fake_session = FakeAiohttpSession(exception=ClientOSError("boom"))
        (flexmock(url_check)
         .should_receive("ClientSession")
         .and_return(fake_session))
        result = await url_check._process_job(job=job)
        assert result.job == job, "wrong job returned"
        assert result.status == 400, "wrong status returned"

    async def test_random_error(self):
        job_id = uuid4().hex
        job = Job(id=job_id, url="url")
        fake_session = FakeAiohttpSession(exception=Exception("boom"))
        (flexmock(url_check)
         .should_receive("ClientSession")
         .and_return(fake_session))
        result = await url_check._process_job(job=job)
        assert result.job == job, "wrong job returned"
        assert result.status == 500, "wrong status returned"

@pytest.mark.consumer
@pytest.mark.asyncio
class TestReceivedJob:
    async def test_ok(self):
        job_id = uuid4().hex
        url = "http://www.google.com"
        message = FakeIncomingMessage(job_id=job_id, url=url)

        fake_session = FakeAiohttpSession(body="body")
        (flexmock(url_check)
         .should_receive("ClientSession")
         .and_return(fake_session))

        (flexmock(url_check)
         .should_call("_validate_message"))

        (flexmock(url_check)
         .should_call("_process_job"))

        await url_check.received_job(message)

        assert message.ack_called, "ack not called"
        assert not message.nack_called, "nack called"
        assert not message.reject_called, "reject called"

    async def test_reject_job(self):
        message = FakeIncomingMessage(body=b"")

        fake_session = FakeAiohttpSession(body="body")
        (flexmock(url_check)
         .should_receive("ClientSession")
         .and_return(fake_session))

        (flexmock(url_check)
         .should_call("_validate_message"))

        (flexmock(url_check)
         .should_call("_process_job"))

        await url_check.received_job(message)

        assert not message.ack_called, "ack called"
        assert not message.nack_called, "nack called"
        assert message.reject_called, "reject called"
        assert not message.reject_requeue, "reject called with requeue=True"

