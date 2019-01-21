from dataclasses import dataclass


@dataclass
class Job:
    id: str
    url: str


@dataclass
class JobResult:
    job: Job
    status: int = None
    size: int = None


class ValidationError(Exception):
    pass