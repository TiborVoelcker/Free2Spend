"""What an importer is.

A Protocol rather than a base class: the shared plumbing is composed from
`csv_table` and `german`, and inheritance would re-couple what splitting them
apart decoupled.

Auto-detection — working out which importer an uploaded file needs — is not
built. It is added by extending this with a `sniff(payload) -> bool` and a
registry of instances; nothing here has to change for that.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from importers.statement import ImportedStatement


@runtime_checkable
class Importer(Protocol):
    name: str

    def parse(self, payload: bytes) -> ImportedStatement:
        """Turn the bytes of an export into a statement."""
        ...
