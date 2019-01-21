import asyncio
import logging
import signal
from asyncio import AbstractEventLoop

import functools
import uvloop

from fm_url_checker.consumer import settings, url_check
from fm_url_checker.consumer.amqp.models import ConnectionArgs, QueueInfo
from fm_url_checker.consumer.amqp.worker import Worker

log = logging.getLogger(__name__)


def shutdown(loop: AbstractEventLoop, sig: int, *async_cleanups):
    log.info(f"Caught signal: {signal.Signals(sig).name}, shutting down")
    if async_cleanups:
        task = asyncio.ensure_future(asyncio.gather(*[func() for func in async_cleanups]))
        task.add_done_callback(lambda *args, **kwargs: loop.stop())


def run():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()

    worker = Worker(connection_args=ConnectionArgs(host=settings.RABBITMQ_HOST,
                                                   port=settings.RABBITMQ_PORT,
                                                   login=settings.RABBITMQ_USER,
                                                   password=settings.RABBITMQ_PASS,
                                                   virtualhost=settings.RABBITMQ_VHOST),
                    prefetch_count=1,
                    loop=loop)

    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig,
                                functools.partial(shutdown, loop, sig, worker.stop))

    loop.create_task(worker.start())
    loop.create_task(worker.register_queue(QueueInfo(name="jobs"), url_check.received_job))

    loop.run_forever()


if __name__ == '__main__':
    run()
