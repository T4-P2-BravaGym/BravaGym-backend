"""Injectable email transport; local outbox is private and never HTTP-served."""

import json
import os
from pathlib import Path
from secrets import token_hex
from typing import Protocol


class EmailSender(Protocol):
    def send(self, *, recipient: str, subject: str, body: str) -> None: ...


class OutboxEmailSender:
    def __init__(self, directory: Path):
        self.directory = directory

    def send(self, *, recipient: str, subject: str, body: str) -> None:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        path = self.directory / f"{token_hex(16)}.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                {"to": recipient, "subject": subject, "body": body},
                stream,
                ensure_ascii=False,
            )


class UnavailableEmailSender:
    def send(self, *, recipient: str, subject: str, body: str) -> None:
        raise RuntimeError(
            "Configure a production EmailSender before enabling recovery delivery"
        )
