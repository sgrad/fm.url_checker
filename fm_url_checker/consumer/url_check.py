import json
import logging
from json import JSONDecodeError

import re
from aio_pika import IncomingMessage
from aiohttp import ClientSession, ClientOSError

from fm_url_checker.consumer.models import Job, JobResult, ValidationError

log = logging.getLogger(__name__)

UUID_REX = re.compile("[0-9a-f]{32}")


def _validate_message(message: IncomingMessage) -> Job:
    """ Basic message validation """

    if not message.content_encoding == "utf8":
        raise ValidationError("Received job with wrong encoding, expecting utf8.")

    job_id = message.headers.get("job_id")
    if not isinstance(job_id, str) or not UUID_REX.match(job_id):
        raise ValidationError(f"Received job with malformed id header: {job_id}.")

    try:
        url = json.loads(message.body.decode("utf8"))["url"]
    except (JSONDecodeError, UnicodeDecodeError, KeyError, TypeError) as e:
        raise ValidationError(f"Received malformed job body, raw: {message.body}. {e.__class__.__name__}: {str(e)}")

    return Job(id=job_id, url=url)


async def _process_job(job: Job) -> JobResult:
    """ Main job processing """

    result = JobResult(job=job)
    async with ClientSession() as session:
        try:
            async with session.get(job.url) as response:
                result.status = response.status

                # Body is automatically unzipped for gzip/deflate encodings
                result.size = len(await response.text())

                # Simulate long running tasks, see readme
                # await asyncio.sleep(10)

        except ClientOSError as e:
            log.error(e)
            result.status = 400
        except Exception as e:
            log.exception(f"Unhandled error occurred: {e}")
            result.status = 500

    return result


async def received_job(message: IncomingMessage) -> None:
    """ AMQP job hook """

    log.info("Received new job", extra=message.info())
    try:
        job = _validate_message(message)
    except ValidationError as e:
        log.error(f"{e}. Rejecting without requeuing", extra=message.info())
        message.reject(requeue=False)
        return

    result = await _process_job(job)
    message.ack()

    log.info("Job completed",
             extra={"job_id": result.job.id,
                    "url": result.job.url,
                    "status": result.status,
                    "size": result.size})
