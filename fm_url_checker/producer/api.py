import json
import logging
from typing import Dict, Tuple, Union
from uuid import uuid4

import re
import rfc3987
from pika import BlockingConnection, ConnectionParameters, PlainCredentials, BasicProperties
from pika.channel import Channel

from fm_url_checker.producer import settings

log = logging.getLogger(__name__)

DOMAIN_REX = re.compile(r"\w+\.\w+")


def _validate_url(url: str) -> None:
    """ Basic url validation """

    if not url:
        raise ValueError("URL is empty")
    url_info = rfc3987.parse(url, rule="URI")

    if url_info["scheme"].lower() not in ("http", "https"):
        raise ValueError("Only accepting http/https URLs")

    if not DOMAIN_REX.match(url_info["authority"]):
        raise ValueError("Invalid domain specified")


def _push_job(url: str) -> str:
    """ Simple method that pushes a job to a rabbitmq queue """

    connection = BlockingConnection(ConnectionParameters(host=settings.RABBITMQ_HOST,
                                                         port=settings.RABBITMQ_PORT,
                                                         virtual_host=settings.RABBITMQ_VHOST,
                                                         credentials=PlainCredentials(username=settings.RABBITMQ_USER,
                                                                                      password=settings.RABBITMQ_PASS)))
    channel: Channel = connection.channel()
    job_id = uuid4().hex
    channel.basic_publish(exchange=settings.RABBITMQ_JOB_EXCHANGE,
                          routing_key=settings.RABBITMQ_JOB_ROUTING_KEY,
                          body=json.dumps({"url": url}),
                          properties=BasicProperties(content_type="application/json",
                                                     content_encoding="utf8",
                                                     headers={"job_id": job_id}))
    connection.close()
    return job_id


def _problem_response(title: str,
                      problem_type: str,
                      detail: str = None,
                      status: int = 400,
                      instance: str = None) -> Tuple[Dict[str, Union[str, int]], int]:
    """ Returns a standard problem response dict and an HTTP status code """

    response = {
        "title": title,
        "type": problem_type,
        "status": status,
    }
    if instance:
        response["instance"] = instance
    if detail:
        response["detail"] = detail
    return response, status


def post(body: Dict[str, str]) -> Tuple[Dict[str, str], int]:
    """ Queue a new url check job """

    log.info("Received new url", extra=body)
    url = body["url"]
    try:
        _validate_url(url)
    except ValueError:
        log.info("Invalid URL received", extra=body)
        return _problem_response(title="Invalid URL provided",
                                 problem_type="fm/error/validation",
                                 detail=f"The specified URL: '{url}' is malformed, expecting rfc3987 formatted url.",
                                 status=400,
                                 instance="fm/error/validation/url")
    job_id = _push_job(url)
    return {"id": job_id}, 201
