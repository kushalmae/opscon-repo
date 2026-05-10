"""
Pydantic schemas for every CSV artifact type.

These are the contracts. If a CSV column drifts, the schema breaks loudly and
the build fails with a clear pointer to the offending row.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class CommandMaster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    opcode: str
    subsystem: str
    criticality: str
    description: str
    fsw_min_version: str


class CommandArg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    arg_position: int
    arg_name: str
    arg_type: str


class CommandEnum(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enum_name: str
    value: int
    label: str
    description: str


class TelemetryMaster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    subsystem: str
    type: str
    units: str = ""
    apid: str
    fsw_min_version: str


class TelemetryDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    description: str


class TelemetryEnum(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    enum_name: str
    value: int
    label: str
    description: str


class TelemetryBitfield(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mnemonic: str
    bit_position: int
    bit_name: str
    description: str


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_id: str
    type: str
    severity: str
    watched_telemetry: str
    condition: str
    description: str
    fdir_id: str = ""
    page: str = ""
    fsw_min_version: str
    owner: str = ""
    created: str = ""
    updated: str = ""
    ack_required: str = ""
    auto_clear: str = ""
    notes: str = ""

    @property
    def watched_list(self) -> list[str]:
        return [s.strip() for s in self.watched_telemetry.split(",") if s.strip()]


class FdirEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fdir_id: str
    title: str
    response: str
    associated_procedure: str = ""
    severity: str
    fsw_min_version: str


class FlightRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    subsystem: str
    rule_text: str
    related_telemetry: str = ""
    operator_action: str
    fsw_min_version: str


class Procedure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    procedure_id: str
    title: str
    type: str
    description: str
    related_commands: str = ""
    related_telemetry: str = ""
    duration_min: int
    criticality: str
    owner: str
    fsw_min_version: str

    @property
    def command_list(self) -> list[str]:
        return [s.strip() for s in self.related_commands.split(",") if s.strip()]

    @property
    def telemetry_list(self) -> list[str]:
        return [s.strip() for s in self.related_telemetry.split(",") if s.strip()]
