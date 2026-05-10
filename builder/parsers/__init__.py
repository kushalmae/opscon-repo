"""
CSV parsers. Each function loads one artifact type, validates every row
against its Pydantic schema, and returns a list of validated records.
Bad rows raise with file/row context.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError

from ..schemas import (
    CommandMaster, CommandArg, CommandEnum,
    TelemetryMaster, TelemetryDescription, TelemetryEnum, TelemetryBitfield,
    Alert, FdirEntry, FlightRule, Procedure,
)

T = TypeVar("T", bound=BaseModel)


class ParseError(Exception):
    pass


def _read_csv(path: Path, schema: Type[T]) -> list[T]:
    """Read a CSV and validate every row against the given schema."""
    if not path.exists():
        raise ParseError(f"Missing required CSV: {path}")
    rows: list[T] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):  # line 1 = header
            # Strip whitespace from values
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            try:
                rows.append(schema(**row))
            except ValidationError as e:
                raise ParseError(
                    f"Validation failed in {path.name} line {line_no}: {e}"
                ) from e
    return rows


def parse_commands(base: Path) -> tuple[list[CommandMaster], list[CommandArg], list[CommandEnum]]:
    return (
        _read_csv(base / "commands" / "commands_master.csv", CommandMaster),
        _read_csv(base / "commands" / "commands_args.csv", CommandArg),
        _read_csv(base / "commands" / "commands_enums.csv", CommandEnum),
    )


def parse_telemetry(base: Path) -> tuple[
    list[TelemetryMaster], list[TelemetryDescription],
    list[TelemetryEnum], list[TelemetryBitfield]
]:
    return (
        _read_csv(base / "telemetry" / "telemetry_master.csv", TelemetryMaster),
        _read_csv(base / "telemetry" / "telemetry_descriptions.csv", TelemetryDescription),
        _read_csv(base / "telemetry" / "telemetry_enums.csv", TelemetryEnum),
        _read_csv(base / "telemetry" / "telemetry_bitfields.csv", TelemetryBitfield),
    )


def parse_alerts(base: Path) -> list[Alert]:
    return _read_csv(base / "alerts" / "alerts.csv", Alert)


def parse_fdir(base: Path) -> list[FdirEntry]:
    return _read_csv(base / "fdir" / "fdir.csv", FdirEntry)


def parse_flight_rules(base: Path) -> list[FlightRule]:
    return _read_csv(base / "flight_rules" / "flight_rules.csv", FlightRule)


def parse_procedures(base: Path) -> list[Procedure]:
    return _read_csv(base / "procedures" / "procedures.csv", Procedure)
