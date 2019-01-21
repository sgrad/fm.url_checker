from dataclasses import dataclass
from uuid import UUID


@dataclass
class QueueInfo:
    name: str
    durable: bool = True

    def __hash__(self):
        return hash(self.name)


@dataclass
class ConnectionArgs:
    host: str = "localhost"
    port: int = 5672
    login: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"
