from dataclasses import dataclass

import aio_pika
import orjson
from aio_pika import DeliveryMode, Message
from fastapi import Request


@dataclass(slots=True)
class RabbitMQPublisher:
    dsn: str
    queue: str
    _connection: aio_pika.abc.AbstractRobustConnection | None = None
    _channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self.dsn)
        self._channel = await self._connection.channel(
            publisher_confirms=True,
            on_return_raises=True,
        )

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._channel = None
        self._connection = None

    def _require_channel(self) -> aio_pika.abc.AbstractChannel:
        if self._channel is None:
            msg = 'rabbitmq channel is not initialized'
            raise RuntimeError(msg)
        return self._channel

    async def publish_job_start(self, *, job_id: str, secret_ref: str, model: str, result_token: str) -> None:
        payload = {
            'type': 'job.start',
            'job_id': job_id,
            'secret_ref': secret_ref,
            'model': model,
            'result_token': result_token,
        }
        channel = self._require_channel()
        await channel.default_exchange.publish(
            Message(
                body=orjson.dumps(payload),
                content_type='application/json',
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=self.queue,
            mandatory=True,
        )


def get_rabbitmq_publisher(request: Request) -> RabbitMQPublisher:
    return request.app.state.rabbitmq
