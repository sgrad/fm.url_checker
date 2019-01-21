import asyncio
import logging
from asyncio import AbstractEventLoop, Task
from typing import Set, Callable, Coroutine

import aio_pika
from aio_pika import Channel, Queue, IncomingMessage
from aio_pika.robust_connection import RobustConnection

from fm_url_checker.consumer.amqp.models import ConnectionArgs, QueueInfo

log = logging.getLogger(__name__)


class BaseTask:
    def __init__(self, loop: AbstractEventLoop = None):
        self._loop = loop or asyncio.get_event_loop()
        self._task: Task = None
        self._stopped = False

    async def start(self):
        self._task = self._loop.create_task(self.main_loop())

    async def stop(self):
        self._stopped = True
        if self._task:
            await self._task

    async def main_loop(self):
        raise NotImplementedError


class Worker(BaseTask):
    def __init__(self,
                 connection_args: ConnectionArgs,
                 prefetch_count: int = 1,
                 prefetch_size: int = 0,
                 loop: AbstractEventLoop = None):
        self._queues: Set[QueueInfo] = set()
        self._connection_args = connection_args
        self._connection: RobustConnection = None
        self._channel: Channel = None
        self._prefetch_count = prefetch_count
        self._prefetch_size = prefetch_size
        self._connection_task: Task = None

        self._close_connection_triggered = False
        super().__init__(loop=loop)

    async def start(self) -> None:
        log.info("Starting worker")
        await self.connect()
        await self._channel.set_qos(prefetch_size=self._prefetch_size,
                                    prefetch_count=self._prefetch_count)
        await super().start()

    async def stop(self):
        if self._connection:
            self._close_connection_triggered = True
            await self._connection.close()
        await super().stop()

    async def register_worker(self):
        await self.connect()

    def connection_lost(self, connection:RobustConnection):
        if not self._close_connection_triggered:
            log.warning(f"Connection to broker lost, attempting reconnection using: {connection}")

    def connection_closed(self, connection:RobustConnection):
        if not self._close_connection_triggered:
            log.warning(f"Closing connection without internal trigger, broker: {connection}")
        else:
            log.info(f"Connection closed, broker: {connection}")

    def connection_reconnected(self, connection:RobustConnection):
        if not self._close_connection_triggered:
            log.info(f"Reacquired connection to broker: {connection}")
        else:
            log.warning(f"Reacquired connection to broker after clean connection close: {connection}")

    async def _connect_channel(self) -> Channel:
        log.info("Connecting worker")
        self._connection: RobustConnection = await aio_pika.connect_robust(**self._connection_args.__dict__,
                                                                           retry_delay=10,
                                                                           connection_attempts=5,
                                                                           socket_timeout=1)
        self._connection.add_connection_lost_callback(callback=self.connection_lost)
        self._connection.add_close_callback(callback=self.connection_closed)
        self._connection.add_reconnect_callback(callback=self.connection_reconnected)
        return await self._connection.channel()

    async def connect(self) -> None:
        connected = False
        if not self._connection_task and (not self._channel or not self._channel.is_open):
            connected = True
            self._connection_task: Task = self._loop.create_task(self._connect_channel())
        self._channel = await self._connection_task
        if connected:
            log.info(f"Connected to broker: {self._connection}")
        self._connection_task = None

    async def register_queue(self, queue_info: QueueInfo, callback: Callable[[IncomingMessage], Coroutine]):
        await self.connect()
        self._queues.add(queue_info)
        queue: Queue = await self._channel.declare_queue(name=queue_info.name,
                                                         durable=queue_info.durable)
        # noinspection PyTypeChecker
        await queue.consume(callback=callback)

    async def main_loop(self):
        pass
