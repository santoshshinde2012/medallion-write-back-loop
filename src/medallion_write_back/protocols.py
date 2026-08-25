"""Contracts between the demo's moving parts (dependency-inversion seams)."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from .models import AgentWrite, CheckResult, PathOutcome


class GoldRepository(Protocol):
    """Owns schema + seed data for the stand-in lakehouse."""

    def connect_and_seed(self) -> sqlite3.Connection: ...


class Validator(Protocol):
    """One check in the write contract (shape / authority / evidence)."""

    @property
    def name(self) -> str: ...

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult: ...


class WritePathStrategy(Protocol):
    """A way an agent's write can reach the platform."""

    @property
    def label(self) -> str: ...

    def apply(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome: ...
