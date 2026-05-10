"""
Resolve cross-references across all artifacts and emit the final JSON bundle.

This is where the magic happens: every command knows which procedures invoke it,
every telemetry point knows which alerts watch it, every FDIR entry knows
its procedure, every flight rule knows its telemetry, and so on.

Unresolved references are collected and reported as warnings (not failures)
because real ops data has dangling refs and you don't want the build to die.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .parsers import (
    parse_commands, parse_telemetry, parse_alerts,
    parse_fdir, parse_flight_rules, parse_procedures,
)


def build_bundle(inputs_root: Path, fsw_version: str) -> tuple[dict, list[str]]:
    """
    Build the resolved JSON bundle for one FSW version.
    Returns (bundle_dict, warnings_list).
    """
    base = inputs_root / f"fsw-v{fsw_version}"
    warnings: list[str] = []

    cmd_master, cmd_args, cmd_enums = parse_commands(base)
    tlm_master, tlm_desc, tlm_enums, tlm_bits = parse_telemetry(base)
    alerts = parse_alerts(base)
    fdir_list = parse_fdir(base)
    flight_rules = parse_flight_rules(base)
    procedures = parse_procedures(base)

    # ----- Index existing IDs for quick lookup
    cmd_set = {c.mnemonic for c in cmd_master}
    tlm_set = {t.mnemonic for t in tlm_master}
    alert_set = {a.alert_id for a in alerts}
    fdir_set = {f.fdir_id for f in fdir_list}
    proc_set = {p.procedure_id for p in procedures}

    # ----- Group child records by parent
    args_by_cmd: dict[str, list[dict]] = defaultdict(list)
    for a in cmd_args:
        args_by_cmd[a.mnemonic].append({
            "position": a.arg_position, "name": a.arg_name, "type": a.arg_type
        })
    for k in args_by_cmd:
        args_by_cmd[k].sort(key=lambda x: x["position"])

    enums_by_cmd_arg: dict[str, list[dict]] = defaultdict(list)
    for e in cmd_enums:
        enums_by_cmd_arg[e.enum_name].append({
            "value": e.value, "label": e.label, "description": e.description
        })

    desc_by_tlm = {d.mnemonic: d.description for d in tlm_desc}
    enums_by_tlm: dict[str, list[dict]] = defaultdict(list)
    for e in tlm_enums:
        enums_by_tlm[e.mnemonic].append({
            "enum_name": e.enum_name, "value": e.value,
            "label": e.label, "description": e.description
        })
    bits_by_tlm: dict[str, list[dict]] = defaultdict(list)
    for b in tlm_bits:
        bits_by_tlm[b.mnemonic].append({
            "bit_position": b.bit_position, "bit_name": b.bit_name,
            "description": b.description
        })
    for k in bits_by_tlm:
        bits_by_tlm[k].sort(key=lambda x: x["bit_position"])

    # ----- Reverse indexes (the cross-reference graph)
    alerts_by_tlm: dict[str, list[str]] = defaultdict(list)
    for a in alerts:
        for tlm in a.watched_list:
            if tlm in tlm_set:
                alerts_by_tlm[tlm].append(a.alert_id)
            else:
                warnings.append(f"Alert {a.alert_id} watches unknown telemetry {tlm}")

    procs_by_cmd: dict[str, list[str]] = defaultdict(list)
    procs_by_tlm: dict[str, list[str]] = defaultdict(list)
    for p in procedures:
        for cmd in p.command_list:
            if cmd in cmd_set:
                procs_by_cmd[cmd].append(p.procedure_id)
            else:
                warnings.append(f"Procedure {p.procedure_id} references unknown command {cmd}")
        for tlm in p.telemetry_list:
            if tlm in tlm_set:
                procs_by_tlm[tlm].append(p.procedure_id)
            else:
                warnings.append(f"Procedure {p.procedure_id} references unknown telemetry {tlm}")

    fdir_by_alert: dict[str, list[str]] = defaultdict(list)
    for a in alerts:
        if a.fdir_id and a.fdir_id in fdir_set:
            fdir_by_alert[a.alert_id].append(a.fdir_id)
        elif a.fdir_id:
            warnings.append(f"Alert {a.alert_id} references unknown FDIR {a.fdir_id}")

    alerts_by_fdir: dict[str, list[str]] = defaultdict(list)
    for a in alerts:
        if a.fdir_id and a.fdir_id in fdir_set:
            alerts_by_fdir[a.fdir_id].append(a.alert_id)

    proc_by_fdir: dict[str, str] = {}
    for f in fdir_list:
        if f.associated_procedure:
            if f.associated_procedure in proc_set:
                proc_by_fdir[f.fdir_id] = f.associated_procedure
            else:
                warnings.append(
                    f"FDIR {f.fdir_id} references unknown procedure {f.associated_procedure}")

    fr_by_tlm: dict[str, list[str]] = defaultdict(list)
    for r in flight_rules:
        if r.related_telemetry:
            if r.related_telemetry in tlm_set:
                fr_by_tlm[r.related_telemetry].append(r.rule_id)
            else:
                warnings.append(
                    f"Flight rule {r.rule_id} references unknown telemetry {r.related_telemetry}")

    # ----- Assemble output records with resolved cross-refs
    out_commands = []
    for c in cmd_master:
        # Find enum tables referenced by any of this command's arg types
        related_enums = []
        for arg in args_by_cmd.get(c.mnemonic, []):
            if arg["type"] in enums_by_cmd_arg:
                related_enums.append({
                    "enum_name": arg["type"],
                    "values": enums_by_cmd_arg[arg["type"]],
                })
        out_commands.append({
            "mnemonic": c.mnemonic,
            "opcode": c.opcode,
            "subsystem": c.subsystem,
            "criticality": c.criticality,
            "description": c.description,
            "fsw_min_version": c.fsw_min_version,
            "args": args_by_cmd.get(c.mnemonic, []),
            "enums": related_enums,
            "used_by_procedures": sorted(set(procs_by_cmd.get(c.mnemonic, []))),
        })

    out_telemetry = []
    for t in tlm_master:
        out_telemetry.append({
            "mnemonic": t.mnemonic,
            "subsystem": t.subsystem,
            "type": t.type,
            "units": t.units,
            "apid": t.apid,
            "fsw_min_version": t.fsw_min_version,
            "description": desc_by_tlm.get(t.mnemonic, ""),
            "enums": enums_by_tlm.get(t.mnemonic, []),
            "bitfields": bits_by_tlm.get(t.mnemonic, []),
            "watched_by_alerts": sorted(set(alerts_by_tlm.get(t.mnemonic, []))),
            "referenced_by_procedures": sorted(set(procs_by_tlm.get(t.mnemonic, []))),
            "referenced_by_flight_rules": sorted(set(fr_by_tlm.get(t.mnemonic, []))),
        })

    out_alerts = []
    for a in alerts:
        out_alerts.append({
            "alert_id": a.alert_id,
            "type": a.type,
            "severity": a.severity,
            "watched_telemetry": a.watched_list,
            "condition": a.condition,
            "description": a.description,
            "fdir_id": a.fdir_id if a.fdir_id in fdir_set else "",
            "page": a.page,
            "owner": a.owner,
            "ack_required": a.ack_required,
            "auto_clear": a.auto_clear,
            "notes": a.notes,
        })

    out_fdir = []
    for f in fdir_list:
        out_fdir.append({
            "fdir_id": f.fdir_id,
            "title": f.title,
            "response": f.response,
            "associated_procedure": (
                f.associated_procedure if f.associated_procedure in proc_set else ""
            ),
            "severity": f.severity,
            "triggered_by_alerts": sorted(set(alerts_by_fdir.get(f.fdir_id, []))),
        })

    out_flight_rules = []
    for r in flight_rules:
        out_flight_rules.append({
            "rule_id": r.rule_id,
            "subsystem": r.subsystem,
            "rule_text": r.rule_text,
            "related_telemetry": r.related_telemetry if r.related_telemetry in tlm_set else "",
            "operator_action": r.operator_action,
        })

    out_procedures = []
    for p in procedures:
        out_procedures.append({
            "procedure_id": p.procedure_id,
            "title": p.title,
            "type": p.type,
            "description": p.description,
            "related_commands": [c for c in p.command_list if c in cmd_set],
            "related_telemetry": [t for t in p.telemetry_list if t in tlm_set],
            "duration_min": p.duration_min,
            "criticality": p.criticality,
            "owner": p.owner,
        })

    bundle = {
        "fsw_version": fsw_version,
        "stats": {
            "commands": len(out_commands),
            "telemetry": len(out_telemetry),
            "alerts": len(out_alerts),
            "fdir": len(out_fdir),
            "flight_rules": len(out_flight_rules),
            "procedures": len(out_procedures),
        },
        "subsystems": sorted({c["subsystem"] for c in out_commands}
                             | {t["subsystem"] for t in out_telemetry}),
        "commands": out_commands,
        "telemetry": out_telemetry,
        "alerts": out_alerts,
        "fdir": out_fdir,
        "flight_rules": out_flight_rules,
        "procedures": out_procedures,
    }

    return bundle, warnings


def write_bundle(bundle: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"bundle.json"
    with open(out_path, "w") as f:
        json.dump(bundle, f, separators=(",", ":"))
    return out_path
