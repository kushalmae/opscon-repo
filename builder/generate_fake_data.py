"""
Generate realistic fake spacecraft ops data with consistent cross-references.

Produces two FSW versions (v1.4, v2.0) so the multi-mission flow is exercised.
v2.0 is a superset of v1.4 with a few new commands/telemetry and one renamed alert.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"

SUBSYSTEMS = ["EPS", "ADCS", "COMM", "CDH", "THERMAL", "PAYLOAD", "PROP"]

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

COMMAND_TEMPLATES = [
    # (subsystem, verb, noun, args, description)
    ("EPS", "PWR", "ON",       [("channel", "uint8"), ("mode", "ENUM_PWR_MODE")],
     "Enable power channel in specified mode"),
    ("EPS", "PWR", "OFF",      [("channel", "uint8")], "Disable power channel"),
    ("EPS", "BATT", "TRICKLE", [("rate_ma", "uint16")], "Set battery trickle charge rate"),
    ("EPS", "BATT", "RESET",   [], "Reset battery management controller"),
    ("EPS", "SOLAR", "DEPLOY", [("array_id", "uint8")], "Deploy solar array"),
    ("EPS", "SOLAR", "STOW",   [("array_id", "uint8")], "Stow solar array"),

    ("ADCS", "MODE", "SET",        [("mode", "ENUM_ADCS_MODE")], "Set ADCS control mode"),
    ("ADCS", "MODE", "SAFE",       [], "Command ADCS into SAFE mode"),
    ("ADCS", "RW", "SPIN",         [("wheel_id", "uint8"), ("rpm", "int16")],
     "Spin reaction wheel to commanded RPM"),
    ("ADCS", "RW", "STOP",         [("wheel_id", "uint8")], "Stop reaction wheel"),
    ("ADCS", "MTQ", "FIRE",        [("axis", "ENUM_MTQ_AXIS"), ("duration_s", "uint16")],
     "Fire magnetorquer along axis"),
    ("ADCS", "STAR", "TRACK",      [("tracker_id", "uint8")], "Begin star tracker tracking"),
    ("ADCS", "ATT", "SLEW",        [("quat_x", "float32"), ("quat_y", "float32"),
                                     ("quat_z", "float32"), ("quat_w", "float32")],
     "Slew to commanded inertial attitude quaternion"),

    ("COMM", "TX", "ENABLE",   [("band", "ENUM_RF_BAND")], "Enable transmitter on band"),
    ("COMM", "TX", "DISABLE",  [("band", "ENUM_RF_BAND")], "Disable transmitter on band"),
    ("COMM", "TX", "POWER",    [("dbm", "int8")], "Set transmitter output power"),
    ("COMM", "DUMP", "START",  [("vc_id", "uint8")], "Start virtual-channel data dump"),
    ("COMM", "DUMP", "STOP",   [("vc_id", "uint8")], "Stop virtual-channel data dump"),

    ("CDH", "BOOT", "WARM",    [], "Warm reboot of flight processor"),
    ("CDH", "BOOT", "COLD",    [], "Cold reboot of flight processor"),
    ("CDH", "TIME", "SYNC",    [("epoch_s", "uint32")], "Sync onboard clock to ground epoch"),
    ("CDH", "FILE", "DELETE",  [("path", "string")], "Delete onboard file by path"),
    ("CDH", "MEM", "DUMP",     [("addr", "uint32"), ("len", "uint16")], "Dump memory region"),
    ("CDH", "MEM", "PATCH",    [("addr", "uint32"), ("data", "bytes")], "Patch memory region"),

    ("THERMAL", "HTR", "ON",   [("heater_id", "uint8")], "Turn on heater zone"),
    ("THERMAL", "HTR", "OFF",  [("heater_id", "uint8")], "Turn off heater zone"),
    ("THERMAL", "HTR", "AUTO", [("heater_id", "uint8")], "Place heater zone in autonomous control"),

    ("PAYLOAD", "IMG", "CAPTURE", [("integration_ms", "uint16"), ("filter", "ENUM_FILTER")],
     "Capture image with integration time and filter"),
    ("PAYLOAD", "IMG", "ABORT",   [], "Abort current image capture"),
    ("PAYLOAD", "INST", "ON",     [], "Power on instrument"),
    ("PAYLOAD", "INST", "OFF",    [], "Power off instrument"),
    ("PAYLOAD", "INST", "CAL",    [("cal_mode", "ENUM_CAL_MODE")], "Run instrument calibration"),

    ("PROP", "VALVE", "OPEN",  [("valve_id", "uint8")], "Open propulsion valve"),
    ("PROP", "VALVE", "CLOSE", [("valve_id", "uint8")], "Close propulsion valve"),
    ("PROP", "BURN", "EXEC",   [("delta_v_ms", "float32"), ("duration_s", "uint16")],
     "Execute commanded delta-v burn"),
    ("PROP", "BURN", "ABORT",  [], "Abort active propulsive maneuver"),
]

# Expand to ~5000 rows by adding numbered variants per channel/array/wheel where applicable
def expand_commands():
    rows = []
    opcode = 0x1000
    for subsystem, verb, noun, args, desc in COMMAND_TEMPLATES:
        # Base command
        mnemonic = f"CMD_{subsystem}_{verb}_{noun}"
        rows.append({
            "mnemonic": mnemonic,
            "opcode": f"0x{opcode:04X}",
            "subsystem": subsystem,
            "criticality": random.choice(["NOMINAL", "NOMINAL", "NOMINAL", "HAZARDOUS", "CRITICAL"]),
            "description": desc,
            "fsw_min_version": "1.0",
            "args": args,
        })
        opcode += 1
    # Pad with synthetic numbered variants to reach ~5000
    base = list(rows)
    n_needed = 5000 - len(rows)
    i = 0
    while len(rows) < 5000:
        proto = base[i % len(base)]
        suffix = i // len(base) + 1
        rows.append({
            "mnemonic": f"{proto['mnemonic']}_{suffix:03d}",
            "opcode": f"0x{opcode:04X}",
            "subsystem": proto["subsystem"],
            "criticality": proto["criticality"],
            "description": f"{proto['description']} (variant {suffix})",
            "fsw_min_version": "1.0",
            "args": proto["args"],
        })
        opcode += 1
        i += 1
    return rows


COMMAND_ENUMS = {
    "ENUM_PWR_MODE":   [(0, "OFF"), (1, "STANDBY"), (2, "NOMINAL"), (3, "BOOST")],
    "ENUM_ADCS_MODE":  [(0, "OFF"), (1, "DETUMBLE"), (2, "SUNPOINT"), (3, "NADIR"),
                        (4, "INERTIAL"), (5, "SAFE")],
    "ENUM_MTQ_AXIS":   [(0, "X_POS"), (1, "X_NEG"), (2, "Y_POS"), (3, "Y_NEG"),
                        (4, "Z_POS"), (5, "Z_NEG")],
    "ENUM_RF_BAND":    [(0, "S_BAND"), (1, "X_BAND"), (2, "UHF")],
    "ENUM_FILTER":     [(0, "CLEAR"), (1, "RED"), (2, "GREEN"), (3, "BLUE"), (4, "NIR")],
    "ENUM_CAL_MODE":   [(0, "DARK"), (1, "FLAT"), (2, "LINEARITY"), (3, "FOCUS")],
}


def write_commands(out_dir: Path, fsw_version: str):
    cmds = expand_commands()

    # Trim a few commands for v1.4 (so v2.0 has the superset)
    if fsw_version == "1.4":
        cmds = [c for c in cmds if "BURN_EXEC" not in c["mnemonic"] or c["mnemonic"] == "CMD_PROP_BURN_EXEC"]
        # Remove all PROP variants except base for v1.4 to make versions distinct
        cmds = [c for c in cmds if not (c["subsystem"] == "PROP" and c["mnemonic"].count("_") > 3)]

    # Master list
    with open(out_dir / "commands_master.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "opcode", "subsystem", "criticality", "description", "fsw_min_version"])
        for c in cmds:
            w.writerow([c["mnemonic"], c["opcode"], c["subsystem"], c["criticality"],
                        c["description"], c["fsw_min_version"]])

    # Args
    with open(out_dir / "commands_args.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "arg_position", "arg_name", "arg_type"])
        for c in cmds:
            for i, (an, at) in enumerate(c["args"]):
                w.writerow([c["mnemonic"], i, an, at])

    # Enums
    with open(out_dir / "commands_enums.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["enum_name", "value", "label", "description"])
        for ename, items in COMMAND_ENUMS.items():
            for val, label in items:
                w.writerow([ename, val, label, f"{ename} value {label}"])


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

TELEMETRY_TEMPLATES = [
    # (mnemonic, subsystem, type, units, desc, [enum_name?], [bitfield_def?])
    ("TLM_EPS_BATT_V",          "EPS", "float32", "V",   "Battery bus voltage"),
    ("TLM_EPS_BATT_I",          "EPS", "float32", "A",   "Battery bus current"),
    ("TLM_EPS_BATT_TEMP",       "EPS", "float32", "degC","Battery cell temperature"),
    ("TLM_EPS_BATT_SOC",        "EPS", "float32", "%",   "Battery state of charge"),
    ("TLM_EPS_SOLAR_V",         "EPS", "float32", "V",   "Solar array bus voltage"),
    ("TLM_EPS_SOLAR_I",         "EPS", "float32", "A",   "Solar array current"),
    ("TLM_EPS_PWR_STATE",       "EPS", "uint8",   "",    "Power channel state bitfield",
     None, "BITS_PWR_STATE"),
    ("TLM_EPS_FAULT_FLAGS",     "EPS", "uint16",  "",    "EPS fault flags",
     None, "BITS_EPS_FAULT"),

    ("TLM_ADCS_MODE",           "ADCS", "uint8",  "",    "ADCS control mode", "ENUM_ADCS_MODE"),
    ("TLM_ADCS_QUAT_X",         "ADCS", "float32", "",    "Estimated attitude quaternion X"),
    ("TLM_ADCS_QUAT_Y",         "ADCS", "float32", "",    "Estimated attitude quaternion Y"),
    ("TLM_ADCS_QUAT_Z",         "ADCS", "float32", "",    "Estimated attitude quaternion Z"),
    ("TLM_ADCS_QUAT_W",         "ADCS", "float32", "",    "Estimated attitude quaternion W"),
    ("TLM_ADCS_RATE_X",         "ADCS", "float32", "deg/s","Body rate about X"),
    ("TLM_ADCS_RATE_Y",         "ADCS", "float32", "deg/s","Body rate about Y"),
    ("TLM_ADCS_RATE_Z",         "ADCS", "float32", "deg/s","Body rate about Z"),
    ("TLM_ADCS_RW1_RPM",        "ADCS", "int16",   "RPM", "Reaction wheel 1 speed"),
    ("TLM_ADCS_RW2_RPM",        "ADCS", "int16",   "RPM", "Reaction wheel 2 speed"),
    ("TLM_ADCS_RW3_RPM",        "ADCS", "int16",   "RPM", "Reaction wheel 3 speed"),
    ("TLM_ADCS_RW4_RPM",        "ADCS", "int16",   "RPM", "Reaction wheel 4 speed"),
    ("TLM_ADCS_STAR_LOCK",      "ADCS", "uint8",   "",    "Star tracker lock status",
     "ENUM_LOCK_STATE"),

    ("TLM_COMM_TX_PWR",         "COMM", "float32", "dBm", "Transmitter output power"),
    ("TLM_COMM_RX_RSSI",        "COMM", "float32", "dBm", "Receiver signal strength"),
    ("TLM_COMM_BAND",           "COMM", "uint8",   "",    "Active RF band", "ENUM_RF_BAND"),
    ("TLM_COMM_LOCK",           "COMM", "uint8",   "",    "Carrier lock status", "ENUM_LOCK_STATE"),
    ("TLM_COMM_BIT_ERR_RATE",   "COMM", "float32", "",    "Bit error rate"),

    ("TLM_CDH_CPU_LOAD",        "CDH", "float32", "%",    "CPU utilization"),
    ("TLM_CDH_MEM_FREE",        "CDH", "uint32",  "B",    "Free memory"),
    ("TLM_CDH_BOOT_COUNT",      "CDH", "uint32",  "",     "Boot counter"),
    ("TLM_CDH_TIME",            "CDH", "uint32",  "s",    "Onboard time since epoch"),
    ("TLM_CDH_FAULT_FLAGS",     "CDH", "uint32",  "",     "CDH fault flags",
     None, "BITS_CDH_FAULT"),

    ("TLM_THERMAL_BUS_TEMP",    "THERMAL", "float32", "degC", "Bus baseplate temperature"),
    ("TLM_THERMAL_RAD_TEMP",    "THERMAL", "float32", "degC", "Radiator temperature"),
    ("TLM_THERMAL_HTR_STATE",   "THERMAL", "uint8",   "",     "Heater state bitfield",
     None, "BITS_HTR_STATE"),

    ("TLM_PAYLOAD_INST_TEMP",   "PAYLOAD", "float32", "degC", "Instrument detector temperature"),
    ("TLM_PAYLOAD_INST_STATE",  "PAYLOAD", "uint8",   "",     "Instrument power/op state",
     "ENUM_INST_STATE"),
    ("TLM_PAYLOAD_IMG_COUNT",   "PAYLOAD", "uint32",  "",     "Images captured this orbit"),
    ("TLM_PAYLOAD_BUFFER_PCT",  "PAYLOAD", "float32", "%",    "Image buffer fill percentage"),

    ("TLM_PROP_TANK_P",         "PROP", "float32", "kPa",  "Propellant tank pressure"),
    ("TLM_PROP_TANK_T",         "PROP", "float32", "degC", "Propellant tank temperature"),
    ("TLM_PROP_VALVE_STATE",    "PROP", "uint8",   "",     "Valve state bitfield",
     None, "BITS_VALVE_STATE"),
    ("TLM_PROP_LAST_DV",        "PROP", "float32", "m/s",  "Last commanded delta-v"),
]


def telemetry_with_overflow(extra: int = 200):
    """Pad telemetry with synthetic per-channel variants to make the catalog feel realistic."""
    out = []
    for tup in TELEMETRY_TEMPLATES:
        # Normalize tuple to length 7 (with optional enum/bitfield)
        padded = tuple(list(tup) + [None] * (7 - len(tup)))
        out.append(padded)
    # Add per-zone heater temps and per-channel currents
    base_idx = 0
    for i in range(extra):
        sub = SUBSYSTEMS[i % len(SUBSYSTEMS)]
        zone = i % 16
        out.append((f"TLM_{sub}_AUX_{zone:02d}", sub, "float32", "raw",
                    f"{sub} auxiliary channel {zone}", None, None))
    return out


TELEM_ENUMS = {
    "ENUM_ADCS_MODE":  [(0, "OFF"), (1, "DETUMBLE"), (2, "SUNPOINT"), (3, "NADIR"),
                        (4, "INERTIAL"), (5, "SAFE")],
    "ENUM_RF_BAND":    [(0, "S_BAND"), (1, "X_BAND"), (2, "UHF")],
    "ENUM_LOCK_STATE": [(0, "UNLOCKED"), (1, "ACQUIRING"), (2, "LOCKED")],
    "ENUM_INST_STATE": [(0, "OFF"), (1, "WARMING"), (2, "READY"), (3, "OBSERVING"), (4, "FAULT")],
}


TELEM_BITFIELDS = {
    "BITS_PWR_STATE": [
        (0, "CH0_ON",  "Power channel 0 enabled"),
        (1, "CH1_ON",  "Power channel 1 enabled"),
        (2, "CH2_ON",  "Power channel 2 enabled"),
        (3, "CH3_ON",  "Power channel 3 enabled"),
        (4, "MAIN_BUS","Main bus enabled"),
        (5, "AUX_BUS", "Auxiliary bus enabled"),
    ],
    "BITS_EPS_FAULT": [
        (0, "OVER_V",     "Overvoltage detected"),
        (1, "UNDER_V",    "Undervoltage detected"),
        (2, "OVER_I",     "Overcurrent detected"),
        (3, "OVER_T",     "Overtemperature detected"),
        (4, "BMS_FAULT",  "Battery management system fault"),
        (5, "ARRAY_FAIL", "Solar array failure detected"),
    ],
    "BITS_CDH_FAULT": [
        (0, "WD_RESET",   "Watchdog timer reset"),
        (1, "MEM_ECC",    "Memory ECC error"),
        (2, "TASK_HUNG",  "Task hung"),
        (3, "FILESYS",    "Filesystem fault"),
        (4, "TIME_JUMP",  "Time discontinuity"),
    ],
    "BITS_HTR_STATE": [
        (0, "BATT_HTR",    "Battery heater on"),
        (1, "PROP_HTR",    "Propellant heater on"),
        (2, "PAYLOAD_HTR", "Payload heater on"),
        (3, "STAR_HTR",    "Star tracker heater on"),
    ],
    "BITS_VALVE_STATE": [
        (0, "V1_OPEN", "Valve 1 open"),
        (1, "V2_OPEN", "Valve 2 open"),
        (2, "V3_OPEN", "Valve 3 open"),
        (3, "V4_OPEN", "Valve 4 open"),
    ],
}


def write_telemetry(out_dir: Path, fsw_version: str):
    rows = telemetry_with_overflow(200 if fsw_version == "2.0" else 150)

    with open(out_dir / "telemetry_master.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "subsystem", "type", "units", "apid", "fsw_min_version"])
        apid = 0x100
        for mn, sub, typ, units, _desc, _enum, _bits in rows:
            w.writerow([mn, sub, typ, units, f"0x{apid:03X}", "1.0"])
            apid += 1

    with open(out_dir / "telemetry_descriptions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "description"])
        for mn, _sub, _typ, _u, desc, _e, _b in rows:
            w.writerow([mn, desc])

    with open(out_dir / "telemetry_enums.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "enum_name", "value", "label", "description"])
        for mn, _sub, _typ, _u, _desc, enum_name, _bits in rows:
            if enum_name and enum_name in TELEM_ENUMS:
                for val, label in TELEM_ENUMS[enum_name]:
                    w.writerow([mn, enum_name, val, label, f"{label} state"])

    with open(out_dir / "telemetry_bitfields.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mnemonic", "bit_position", "bit_name", "description"])
        for mn, _sub, _typ, _u, _desc, _enum, bit_def in rows:
            if bit_def and bit_def in TELEM_BITFIELDS:
                for bp, bn, bd in TELEM_BITFIELDS[bit_def]:
                    w.writerow([mn, bp, bn, bd])


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

ALERT_TEMPLATES = [
    # (id, type, severity, watched_telemetry, condition_expr, description, fdir_id, page)
    ("ALT_EPS_001", "threshold", "WARNING",  "TLM_EPS_BATT_V",         "value < 24.5",
     "Battery voltage low",                                "FDIR_EPS_001", "EPS_OVERVIEW"),
    ("ALT_EPS_002", "threshold", "CRITICAL", "TLM_EPS_BATT_V",         "value < 22.0",
     "Battery voltage critically low",                     "FDIR_EPS_002", "EPS_OVERVIEW"),
    ("ALT_EPS_003", "threshold", "WARNING",  "TLM_EPS_BATT_TEMP",      "value > 45.0",
     "Battery temperature high",                           "FDIR_EPS_003", "EPS_THERMAL"),
    ("ALT_EPS_004", "threshold", "WARNING",  "TLM_EPS_BATT_SOC",       "value < 30.0",
     "Battery state of charge low",                        "FDIR_EPS_001", "EPS_OVERVIEW"),
    ("ALT_EPS_005", "rule",      "CRITICAL", "TLM_EPS_FAULT_FLAGS",    "bit(OVER_V) == 1",
     "EPS overvoltage fault flag set",                     "FDIR_EPS_004", "EPS_FAULTS"),
    ("ALT_EPS_006", "rule",      "CRITICAL", "TLM_EPS_FAULT_FLAGS",    "bit(BMS_FAULT) == 1",
     "Battery management system fault",                    "FDIR_EPS_002", "EPS_FAULTS"),
    ("ALT_EPS_007", "derived",   "WARNING",  "TLM_EPS_BATT_V,TLM_EPS_BATT_I",
     "TLM_EPS_BATT_V * TLM_EPS_BATT_I < 50",
     "Battery delivering insufficient power",              "FDIR_EPS_001", "EPS_OVERVIEW"),

    ("ALT_ADCS_001", "rule",      "CRITICAL", "TLM_ADCS_MODE",         "value == SAFE",
     "ADCS in SAFE mode",                                  "FDIR_ADCS_001", "ADCS_OVERVIEW"),
    ("ALT_ADCS_002", "threshold", "WARNING",  "TLM_ADCS_RATE_X",       "abs(value) > 2.0",
     "Body rate X exceeds nominal",                        "FDIR_ADCS_002", "ADCS_OVERVIEW"),
    ("ALT_ADCS_003", "threshold", "WARNING",  "TLM_ADCS_RATE_Y",       "abs(value) > 2.0",
     "Body rate Y exceeds nominal",                        "FDIR_ADCS_002", "ADCS_OVERVIEW"),
    ("ALT_ADCS_004", "threshold", "WARNING",  "TLM_ADCS_RATE_Z",       "abs(value) > 2.0",
     "Body rate Z exceeds nominal",                        "FDIR_ADCS_002", "ADCS_OVERVIEW"),
    ("ALT_ADCS_005", "threshold", "CRITICAL", "TLM_ADCS_RW1_RPM",      "abs(value) > 6000",
     "Reaction wheel 1 saturating",                        "FDIR_ADCS_003", "ADCS_RW"),
    ("ALT_ADCS_006", "threshold", "CRITICAL", "TLM_ADCS_RW2_RPM",      "abs(value) > 6000",
     "Reaction wheel 2 saturating",                        "FDIR_ADCS_003", "ADCS_RW"),
    ("ALT_ADCS_007", "rule",      "WARNING",  "TLM_ADCS_STAR_LOCK",    "value != LOCKED",
     "Star tracker not locked",                            "FDIR_ADCS_004", "ADCS_OVERVIEW"),

    ("ALT_COMM_001", "threshold", "WARNING",  "TLM_COMM_RX_RSSI",      "value < -120",
     "Receiver signal strength low",                       "FDIR_COMM_001", "COMM_LINK"),
    ("ALT_COMM_002", "threshold", "WARNING",  "TLM_COMM_BIT_ERR_RATE", "value > 1e-5",
     "Bit error rate exceeds threshold",                   "FDIR_COMM_002", "COMM_LINK"),
    ("ALT_COMM_003", "rule",      "WARNING",  "TLM_COMM_LOCK",         "value != LOCKED",
     "Carrier lock lost",                                  "FDIR_COMM_001", "COMM_LINK"),

    ("ALT_CDH_001",  "threshold", "WARNING",  "TLM_CDH_CPU_LOAD",      "value > 80",
     "CPU load high",                                      "FDIR_CDH_001",  "CDH_HEALTH"),
    ("ALT_CDH_002",  "threshold", "CRITICAL", "TLM_CDH_CPU_LOAD",      "value > 95",
     "CPU load critical",                                  "FDIR_CDH_001",  "CDH_HEALTH"),
    ("ALT_CDH_003",  "threshold", "WARNING",  "TLM_CDH_MEM_FREE",      "value < 1048576",
     "Free memory low",                                    "FDIR_CDH_002",  "CDH_HEALTH"),
    ("ALT_CDH_004",  "rule",      "CRITICAL", "TLM_CDH_FAULT_FLAGS",   "bit(WD_RESET) == 1",
     "Watchdog reset detected",                            "FDIR_CDH_003",  "CDH_FAULTS"),
    ("ALT_CDH_005",  "rule",      "CRITICAL", "TLM_CDH_FAULT_FLAGS",   "bit(MEM_ECC) == 1",
     "Memory ECC error",                                   "FDIR_CDH_004",  "CDH_FAULTS"),

    ("ALT_THM_001",  "threshold", "WARNING",  "TLM_THERMAL_BUS_TEMP",  "value > 50.0",
     "Bus temperature high",                               "FDIR_THM_001",  "THERMAL_OVERVIEW"),
    ("ALT_THM_002",  "threshold", "WARNING",  "TLM_THERMAL_BUS_TEMP",  "value < -10.0",
     "Bus temperature low",                                "FDIR_THM_002",  "THERMAL_OVERVIEW"),
    ("ALT_THM_003",  "threshold", "CRITICAL", "TLM_THERMAL_RAD_TEMP",  "value > 80.0",
     "Radiator temperature critical",                      "FDIR_THM_001",  "THERMAL_OVERVIEW"),

    ("ALT_PAY_001",  "threshold", "WARNING",  "TLM_PAYLOAD_INST_TEMP", "value > 25.0",
     "Instrument detector temperature high",               "FDIR_PAY_001",  "PAYLOAD_HEALTH"),
    ("ALT_PAY_002",  "rule",      "WARNING",  "TLM_PAYLOAD_INST_STATE", "value == FAULT",
     "Instrument in FAULT state",                          "FDIR_PAY_002",  "PAYLOAD_HEALTH"),
    ("ALT_PAY_003",  "threshold", "WARNING",  "TLM_PAYLOAD_BUFFER_PCT", "value > 90",
     "Image buffer near full",                             "FDIR_PAY_003",  "PAYLOAD_DATA"),

    ("ALT_PROP_001", "threshold", "CRITICAL", "TLM_PROP_TANK_P",       "value > 2200",
     "Propellant tank overpressure",                       "FDIR_PROP_001", "PROP_OVERVIEW"),
    ("ALT_PROP_002", "threshold", "WARNING",  "TLM_PROP_TANK_P",       "value < 800",
     "Propellant tank pressure low",                       "FDIR_PROP_002", "PROP_OVERVIEW"),
    ("ALT_PROP_003", "threshold", "WARNING",  "TLM_PROP_TANK_T",       "value < 5.0",
     "Propellant temperature near freezing",               "FDIR_PROP_003", "PROP_OVERVIEW"),
]


def write_alerts(out_dir: Path, fsw_version: str):
    alerts = list(ALERT_TEMPLATES)
    # v2.0 adds a few more, renames one
    if fsw_version == "2.0":
        alerts.append(("ALT_EPS_008", "derived", "WARNING",
                       "TLM_EPS_BATT_V,TLM_EPS_BATT_TEMP",
                       "value(TLM_EPS_BATT_V) < 25.0 and value(TLM_EPS_BATT_TEMP) > 40",
                       "Hot battery under load", "FDIR_EPS_001", "EPS_OVERVIEW"))
    # Pad to ~1000 with synthetic per-channel alerts
    fdir_prefix_map = {"EPS": "EPS", "ADCS": "ADCS", "COMM": "COMM",
                       "CDH": "CDH", "THERMAL": "THM", "PAYLOAD": "PAY", "PROP": "PROP"}
    while len(alerts) < 1000:
        i = len(alerts)
        sub = SUBSYSTEMS[i % len(SUBSYSTEMS)]
        zone = i % 16
        alerts.append((f"ALT_{sub}_AUX_{i:04d}", "threshold", "WARNING",
                       f"TLM_{sub}_AUX_{zone:02d}", "value > 1000",
                       f"{sub} auxiliary {zone} out of range",
                       f"FDIR_{fdir_prefix_map[sub]}_001", f"{sub}_OVERVIEW"))

    with open(out_dir / "alerts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alert_id", "type", "severity", "watched_telemetry", "condition",
                    "description", "fdir_id", "page", "fsw_min_version", "owner",
                    "created", "updated", "ack_required", "auto_clear", "notes"])
        for a in alerts:
            aid, atype, sev, watched, cond, desc, fdir, page = a
            w.writerow([aid, atype, sev, watched, cond, desc, fdir, page,
                        "1.0", "ops-team", "2024-01-15", "2024-09-01",
                        "yes" if sev == "CRITICAL" else "no", "yes",
                        "auto-generated" if "AUX" in aid else ""])


# ---------------------------------------------------------------------------
# FDIR
# ---------------------------------------------------------------------------

FDIR_TEMPLATES = [
    ("FDIR_EPS_001", "Low battery", "Reduce non-essential loads, command CMD_EPS_PWR_OFF for low-priority channels",
     "PROC_EPS_LOAD_SHED"),
    ("FDIR_EPS_002", "Battery management fault", "Power cycle BMS via CMD_EPS_BATT_RESET, monitor TLM_EPS_BATT_V",
     "PROC_EPS_BMS_RECOVERY"),
    ("FDIR_EPS_003", "Battery overtemperature", "Disable charging via CMD_EPS_BATT_TRICKLE rate=0",
     "PROC_EPS_BATT_THERMAL"),
    ("FDIR_EPS_004", "EPS overvoltage", "Isolate affected channel via CMD_EPS_PWR_OFF",
     "PROC_EPS_OVERVOLTAGE"),

    ("FDIR_ADCS_001", "ADCS in SAFE", "Verify spacecraft state, command CMD_ADCS_MODE_SET to recover",
     "PROC_ADCS_SAFE_RECOVERY"),
    ("FDIR_ADCS_002", "Body rates exceed nominal", "Engage detumble via CMD_ADCS_MODE_SET mode=DETUMBLE",
     "PROC_ADCS_DETUMBLE"),
    ("FDIR_ADCS_003", "Reaction wheel saturation", "Fire magnetorquers via CMD_ADCS_MTQ_FIRE for momentum dump",
     "PROC_ADCS_MOMENTUM_DUMP"),
    ("FDIR_ADCS_004", "Star tracker lost lock", "Reissue CMD_ADCS_STAR_TRACK, verify TLM_ADCS_STAR_LOCK",
     "PROC_ADCS_STAR_REACQ"),

    ("FDIR_COMM_001", "Link degraded", "Switch RF band via CMD_COMM_TX_ENABLE, increase power via CMD_COMM_TX_POWER",
     "PROC_COMM_LINK_RECOVERY"),
    ("FDIR_COMM_002", "High BER", "Reduce data rate, switch to redundant transmitter",
     "PROC_COMM_BER_MITIGATION"),

    ("FDIR_CDH_001", "CPU overload", "Suspend non-essential tasks, dump task list",
     "PROC_CDH_CPU_RECOVERY"),
    ("FDIR_CDH_002", "Memory low", "Run cleanup, delete temp files via CMD_CDH_FILE_DELETE",
     "PROC_CDH_MEM_CLEANUP"),
    ("FDIR_CDH_003", "Watchdog reset", "Inspect TLM_CDH_BOOT_COUNT, dump memory via CMD_CDH_MEM_DUMP",
     "PROC_CDH_WD_INVESTIGATION"),
    ("FDIR_CDH_004", "Memory ECC error", "Dump affected region, schedule CMD_CDH_MEM_PATCH if persistent",
     "PROC_CDH_ECC_RECOVERY"),

    ("FDIR_THM_001", "Thermal high", "Engage radiator, reduce active loads",
     "PROC_THM_HOT_RECOVERY"),
    ("FDIR_THM_002", "Thermal low", "Enable heaters via CMD_THERMAL_HTR_ON",
     "PROC_THM_COLD_RECOVERY"),

    ("FDIR_PAY_001", "Detector hot", "Suspend imaging, allow cooldown, monitor TLM_PAYLOAD_INST_TEMP",
     "PROC_PAY_THERMAL_HOLD"),
    ("FDIR_PAY_002", "Instrument fault", "Power cycle via CMD_PAYLOAD_INST_OFF then CMD_PAYLOAD_INST_ON",
     "PROC_PAY_RECOVERY"),
    ("FDIR_PAY_003", "Buffer full", "Initiate dump via CMD_COMM_DUMP_START",
     "PROC_PAY_BUFFER_DUMP"),

    ("FDIR_PROP_001", "Tank overpressure", "Vent via CMD_PROP_VALVE_OPEN, monitor TLM_PROP_TANK_P",
     "PROC_PROP_VENT"),
    ("FDIR_PROP_002", "Tank underpressure", "Halt all burn planning, escalate to engineering",
     "PROC_PROP_LOW_P_HOLD"),
    ("FDIR_PROP_003", "Propellant cold", "Enable propellant heater via CMD_THERMAL_HTR_ON id=PROP",
     "PROC_PROP_THERMAL"),
]


def write_fdir(out_dir: Path, fsw_version: str):
    with open(out_dir / "fdir.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fdir_id", "title", "response", "associated_procedure",
                    "severity", "fsw_min_version"])
        for fid, title, resp, proc in FDIR_TEMPLATES:
            sev = "CRITICAL" if "fault" in title.lower() or "saturation" in title.lower() else "WARNING"
            w.writerow([fid, title, resp, proc, sev, "1.0"])


# ---------------------------------------------------------------------------
# Flight rules
# ---------------------------------------------------------------------------

FLIGHT_RULES = [
    ("FR_EPS_001", "EPS", "Battery shall not be discharged below 22.0 V during eclipse",
     "TLM_EPS_BATT_V", "Operator must verify SOC > 30% before entering eclipse"),
    ("FR_EPS_002", "EPS", "Solar array deployment shall not be commanded while in eclipse",
     "TLM_EPS_SOLAR_V", "Verify solar voltage > 0 before CMD_EPS_SOLAR_DEPLOY"),
    ("FR_ADCS_001", "ADCS", "Reaction wheel commanded RPM shall not exceed +/- 5500",
     "TLM_ADCS_RW1_RPM", "Limit CMD_ADCS_RW_SPIN argument to within bounds"),
    ("FR_ADCS_002", "ADCS", "ADCS mode transition to INERTIAL requires star tracker lock",
     "TLM_ADCS_STAR_LOCK", "Verify TLM_ADCS_STAR_LOCK == LOCKED before CMD_ADCS_MODE_SET INERTIAL"),
    ("FR_COMM_001", "COMM", "Transmitter shall not be enabled while ground station is below 5 deg elevation",
     "TLM_COMM_TX_PWR", "AOS verification required before CMD_COMM_TX_ENABLE"),
    ("FR_CDH_001", "CDH", "Memory patches shall be uplinked only during contact passes with full uplink margin",
     "TLM_CDH_MEM_FREE", "Operator must obtain second-operator concurrence for CMD_CDH_MEM_PATCH"),
    ("FR_THM_001", "THERMAL", "Battery heater shall remain on whenever battery temperature < 5 degC",
     "TLM_EPS_BATT_TEMP", "FDIR_THM_002 will autonomously enable; verify within 30s"),
    ("FR_PAY_001", "PAYLOAD", "Imaging shall not be commanded while ADCS is in SAFE",
     "TLM_ADCS_MODE", "Verify TLM_ADCS_MODE != SAFE before CMD_PAYLOAD_IMG_CAPTURE"),
    ("FR_PAY_002", "PAYLOAD", "Instrument shall not be powered on while detector temperature > 20 degC",
     "TLM_PAYLOAD_INST_TEMP", "Wait for cooldown before CMD_PAYLOAD_INST_ON"),
    ("FR_PROP_001", "PROP", "Burns shall not be executed with tank pressure < 1000 kPa",
     "TLM_PROP_TANK_P", "Verify pressure prior to CMD_PROP_BURN_EXEC"),
    ("FR_PROP_002", "PROP", "Burns require dual operator concurrence",
     None, "Two operators must both confirm before CMD_PROP_BURN_EXEC"),
    ("FR_PROP_003", "PROP", "Propellant temperature shall remain above 5 degC at all times",
     "TLM_PROP_TANK_T", "Heater per FDIR_PROP_003"),
]


def write_flight_rules(out_dir: Path, fsw_version: str):
    with open(out_dir / "flight_rules.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rule_id", "subsystem", "rule_text", "related_telemetry",
                    "operator_action", "fsw_min_version"])
        for rid, sub, txt, tlm, action in FLIGHT_RULES:
            w.writerow([rid, sub, txt, tlm or "", action, "1.0"])


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------

PROCEDURES = [
    # (id, title, type, description, related_commands, related_telemetry, duration_min, criticality)
    ("PROC_EPS_LOAD_SHED",         "EPS load shed", "python",
     "Drop non-essential loads to preserve battery during contingency",
     "CMD_EPS_PWR_OFF", "TLM_EPS_BATT_V,TLM_EPS_BATT_SOC", 5, "HAZARDOUS"),
    ("PROC_EPS_BMS_RECOVERY",      "BMS recovery", "python",
     "Power-cycle the battery management system and verify telemetry",
     "CMD_EPS_BATT_RESET", "TLM_EPS_BATT_V,TLM_EPS_BATT_TEMP,TLM_EPS_FAULT_FLAGS", 10, "CRITICAL"),
    ("PROC_EPS_BATT_THERMAL",      "Battery thermal recovery", "python",
     "Reduce charging current and engage cooling pathway",
     "CMD_EPS_BATT_TRICKLE", "TLM_EPS_BATT_TEMP", 15, "HAZARDOUS"),
    ("PROC_EPS_OVERVOLTAGE",       "EPS overvoltage isolation", "python",
     "Isolate the offending channel and inspect fault flags",
     "CMD_EPS_PWR_OFF", "TLM_EPS_FAULT_FLAGS,TLM_EPS_BATT_V", 8, "CRITICAL"),

    ("PROC_ADCS_SAFE_RECOVERY",    "ADCS SAFE recovery", "abstract",
     "High-level recovery wrapper: verify state, run detumble, return to NADIR",
     "CMD_ADCS_MODE_SET", "TLM_ADCS_MODE,TLM_ADCS_RATE_X,TLM_ADCS_RATE_Y,TLM_ADCS_RATE_Z", 30, "CRITICAL"),
    ("PROC_ADCS_DETUMBLE",         "ADCS detumble", "python",
     "Execute detumble mode and verify body rates converge",
     "CMD_ADCS_MODE_SET,CMD_ADCS_MTQ_FIRE",
     "TLM_ADCS_RATE_X,TLM_ADCS_RATE_Y,TLM_ADCS_RATE_Z", 20, "HAZARDOUS"),
    ("PROC_ADCS_MOMENTUM_DUMP",    "Reaction wheel momentum dump", "python",
     "Use magnetorquers to bleed off accumulated wheel momentum",
     "CMD_ADCS_MTQ_FIRE,CMD_ADCS_RW_SPIN",
     "TLM_ADCS_RW1_RPM,TLM_ADCS_RW2_RPM,TLM_ADCS_RW3_RPM,TLM_ADCS_RW4_RPM", 25, "NOMINAL"),
    ("PROC_ADCS_STAR_REACQ",       "Star tracker reacquisition", "python",
     "Reissue tracking command and verify lock",
     "CMD_ADCS_STAR_TRACK", "TLM_ADCS_STAR_LOCK", 10, "NOMINAL"),

    ("PROC_COMM_LINK_RECOVERY",    "Comm link recovery", "abstract",
     "Stepwise recovery: verify pointing, switch band, increase power",
     "CMD_COMM_TX_ENABLE,CMD_COMM_TX_POWER",
     "TLM_COMM_RX_RSSI,TLM_COMM_LOCK,TLM_COMM_BIT_ERR_RATE", 15, "NOMINAL"),
    ("PROC_COMM_BER_MITIGATION",   "BER mitigation", "python",
     "Reduce data rate, fall back to redundant TX",
     "CMD_COMM_TX_POWER", "TLM_COMM_BIT_ERR_RATE", 10, "NOMINAL"),

    ("PROC_CDH_CPU_RECOVERY",      "CDH CPU recovery", "python",
     "Identify hung tasks and suspend non-essential workloads",
     "", "TLM_CDH_CPU_LOAD,TLM_CDH_FAULT_FLAGS", 10, "HAZARDOUS"),
    ("PROC_CDH_MEM_CLEANUP",       "CDH memory cleanup", "python",
     "Delete temporary files and dump usage report",
     "CMD_CDH_FILE_DELETE", "TLM_CDH_MEM_FREE", 8, "NOMINAL"),
    ("PROC_CDH_WD_INVESTIGATION",  "Watchdog investigation", "abstract",
     "Manual checklist + dump memory regions for ground review",
     "CMD_CDH_MEM_DUMP", "TLM_CDH_BOOT_COUNT,TLM_CDH_FAULT_FLAGS", 45, "CRITICAL"),
    ("PROC_CDH_ECC_RECOVERY",      "Memory ECC recovery", "python",
     "Dump affected region; if persistent, schedule patch",
     "CMD_CDH_MEM_DUMP,CMD_CDH_MEM_PATCH", "TLM_CDH_FAULT_FLAGS", 30, "CRITICAL"),

    ("PROC_THM_HOT_RECOVERY",      "Thermal hot recovery", "python",
     "Reduce active loads and verify radiator pathway",
     "CMD_THERMAL_HTR_OFF,CMD_PAYLOAD_INST_OFF",
     "TLM_THERMAL_BUS_TEMP,TLM_THERMAL_RAD_TEMP", 20, "HAZARDOUS"),
    ("PROC_THM_COLD_RECOVERY",     "Thermal cold recovery", "python",
     "Enable heaters and monitor return to nominal range",
     "CMD_THERMAL_HTR_ON", "TLM_THERMAL_BUS_TEMP,TLM_EPS_BATT_TEMP", 20, "NOMINAL"),

    ("PROC_PAY_THERMAL_HOLD",      "Payload thermal hold", "python",
     "Suspend imaging until detector cools",
     "CMD_PAYLOAD_IMG_ABORT", "TLM_PAYLOAD_INST_TEMP", 15, "NOMINAL"),
    ("PROC_PAY_RECOVERY",          "Payload recovery", "abstract",
     "Power-cycle instrument, run cal, verify nominal operation",
     "CMD_PAYLOAD_INST_OFF,CMD_PAYLOAD_INST_ON,CMD_PAYLOAD_INST_CAL",
     "TLM_PAYLOAD_INST_STATE,TLM_PAYLOAD_INST_TEMP", 30, "HAZARDOUS"),
    ("PROC_PAY_BUFFER_DUMP",       "Payload buffer dump", "python",
     "Initiate dump of stored imagery during next contact",
     "CMD_COMM_DUMP_START,CMD_COMM_DUMP_STOP",
     "TLM_PAYLOAD_BUFFER_PCT", 60, "NOMINAL"),

    ("PROC_PROP_VENT",             "Propellant tank vent", "abstract",
     "Controlled venting with operator concurrence",
     "CMD_PROP_VALVE_OPEN,CMD_PROP_VALVE_CLOSE", "TLM_PROP_TANK_P", 30, "CRITICAL"),
    ("PROC_PROP_LOW_P_HOLD",       "Low pressure hold", "abstract",
     "Halt burn planning, escalate to engineering review",
     "", "TLM_PROP_TANK_P", 60, "CRITICAL"),
    ("PROC_PROP_THERMAL",          "Propellant thermal", "python",
     "Enable propellant heater zone and verify warming trend",
     "CMD_THERMAL_HTR_ON", "TLM_PROP_TANK_T", 25, "NOMINAL"),
]


def write_procedures(out_dir: Path, fsw_version: str):
    with open(out_dir / "procedures.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["procedure_id", "title", "type", "description",
                    "related_commands", "related_telemetry",
                    "duration_min", "criticality", "owner", "fsw_min_version"])
        for p in PROCEDURES:
            pid, title, ptype, desc, cmds, tlm, dur, crit = p
            w.writerow([pid, title, ptype, desc, cmds, tlm, dur, crit, "ops-team", "1.0"])


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_one(fsw_version: str):
    base = INPUTS / f"fsw-v{fsw_version}"
    write_commands(base / "commands", fsw_version)
    write_telemetry(base / "telemetry", fsw_version)
    write_alerts(base / "alerts", fsw_version)
    write_fdir(base / "fdir", fsw_version)
    write_flight_rules(base / "flight_rules", fsw_version)
    write_procedures(base / "procedures", fsw_version)
    print(f"Generated FSW v{fsw_version}")


if __name__ == "__main__":
    build_one("1.4")
    build_one("2.0")
