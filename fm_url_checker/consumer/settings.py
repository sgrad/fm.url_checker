import logging

import os

# noinspection PyUnresolvedReferences
from . import logging_config

log = logging.getLogger(__name__)

NAME = "api:check_url"

DEBUG = (os.getenv("FM_DEBUG", "false").lower() in ("y", "yes", "t", "true"))

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5762"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "rabbitmq")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "rabbitmq")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_JOB_EXCHANGE = os.getenv("RABBITMQ_JOB_EXCHANGE", "")
RABBITMQ_JOB_ROUTING_KEY = os.getenv("RABBITMQ_JOB_ROUTING_KEY", "jobs")

if DEBUG:
    logging.getLogger("").setLevel("DEBUG")
