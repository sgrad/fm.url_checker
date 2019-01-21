import json
from uuid import uuid4

import pytest
import re
from flexmock import flexmock
from pika import BasicProperties

from fm_url_checker.producer import api as producer_api, settings

UUID_REX = re.compile(r"[0-9a-f]{32}")


class FakePikaChannel:
    def __init__(self):
        self.exchange = None
        self.routing_key = None
        self.body = None
        self.properties = None
        self.extra_args = None
        self.extra_kwargs = None

    def basic_publish(self, exchange, routing_key, body, properties=None, *args, **kwargs):
        self.exchange = exchange
        self.routing_key = routing_key
        self.body = body
        self.properties = properties
        self.extra_args = args
        self.extra_kwargs = kwargs


class FakePikaConnection:
    def __init__(self, channel_instance=None):
        self.channel_called: bool = False
        self.close_called: bool = False
        self.channel_instance = channel_instance or FakePikaChannel()

    def channel(self):
        self.channel_called = True
        return self.channel_instance

    def close(self):
        self.close_called = True
        pass


@pytest.mark.producer
class TestValidation:
    def test_valid_url(self):
        assert producer_api._validate_url("http://google.com") is None
        assert producer_api._validate_url("https://google.com") is None
        assert producer_api._validate_url("HTTP://google.com") is None
        assert producer_api._validate_url("HTTPs://google.com") is None
        assert producer_api._validate_url("HTTPS://google.com") is None

    def test_invalid_url_schema(self):
        with pytest.raises(ValueError, match=".*accepting http/https.*"):
            # noinspection SpellCheckingInspection
            producer_api._validate_url("httpss://google.com")
        with pytest.raises(ValueError, match=".*accepting http/https.*"):
            producer_api._validate_url("ftp://google.com")
        with pytest.raises(ValueError, match=".*accepting http/https.*"):
            producer_api._validate_url("bad://google.com")

    def test_invalid_url_empty(self):
        with pytest.raises(ValueError, match=".*empty.*"):
            producer_api._validate_url("")

    def test_invalid_url_domain(self):
        with pytest.raises(ValueError, match=".*domain.*"):
            producer_api._validate_url("http://")
        with pytest.raises(ValueError, match=".*domain.*"):
            producer_api._validate_url("http://a")
        with pytest.raises(ValueError, match=".*domain.*"):
            producer_api._validate_url("http://a.")
        with pytest.raises(ValueError, match=".*domain.*"):
            producer_api._validate_url("http://.a")


@pytest.mark.producer
class TestJobQueueing:
    def test_ok(self):
        fake_channel = FakePikaChannel()
        fake_connection = FakePikaConnection(channel_instance=fake_channel)

        (flexmock(producer_api)
         .should_receive("BlockingConnection")
         .and_return(fake_connection))

        url = "https://google.com"

        assert UUID_REX.match(producer_api._push_job(url)) is not None

        assert fake_connection.channel_called, "channel was never acquired"
        assert fake_connection.close_called, "connection was not closed"

        assert fake_channel.exchange == settings.RABBITMQ_JOB_EXCHANGE, "wrong exchange used"
        assert fake_channel.routing_key == settings.RABBITMQ_JOB_ROUTING_KEY, "wrong routing_key used"
        assert fake_channel.body == json.dumps({"url": url}), "malformed job body"
        assert isinstance(fake_channel.properties, BasicProperties), "basic properties not provided"
        assert UUID_REX.match(fake_channel.properties.headers.get("job_id")), "job_id not included in header"


@pytest.mark.producer
class TestAPI:
    def test_ok(self):
        url = "https://google.com"
        job_id = uuid4()

        (flexmock(producer_api)
         .should_receive("_push_job")
         .with_args(url)
         .and_return(job_id))

        (flexmock(producer_api)
         .should_call("_validate_url")
         .with_args(url))

        response, status = producer_api.post({"url": url})
        assert isinstance(response, dict), "post didn't return a response dict"
        assert isinstance(status, int), "post didn't return an int status"

        assert response.get("id") == job_id, "response didn't contain job id"
        assert status == 201, "bad response status"

    def test_error(self):
        # noinspection SpellCheckingInspection
        url = "httpss://google.com"
        job_id = uuid4()

        (flexmock(producer_api)
         .should_receive("_push_job")
         .with_args(url)
         .and_return(job_id))

        (flexmock(producer_api)
         .should_call("_validate_url")
         .with_args(url))

        response, status = producer_api.post({"url": url})

        assert isinstance(response, dict), "post didn't return a response dict"
        assert isinstance(status, int), "post didn't return an int status"

        assert not {"title", "type", "status"}.difference(set(response.keys())), "response is missing required keys"
        assert response.get("status") == status == 400, "response didn't return correct status"
