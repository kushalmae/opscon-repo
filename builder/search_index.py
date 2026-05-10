"""
Build a compact full-text search index.

We ship our own tiny index instead of pulling MiniSearch/Lunr from a CDN.
Format: { tokens: { token: [docId, docId, ...] }, docs: [{id, kind, title, subtitle, sub}] }

The frontend does fuzzy matching on tokens (prefix + Levenshtein-1).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def build_index(bundle: dict) -> dict:
    docs = []  # [{id, kind, title, subtitle, sub}]
    inv: dict[str, set[int]] = {}

    def add(doc_id: str, kind: str, title: str, subtitle: str, subsystem: str, blob: str):
        idx = len(docs)
        docs.append({
            "id": doc_id, "kind": kind, "title": title,
            "subtitle": subtitle, "sub": subsystem,
        })
        for tok in set(tokenize(blob)):
            inv.setdefault(tok, set()).add(idx)

    for c in bundle["commands"]:
        add(c["mnemonic"], "command", c["mnemonic"], c["description"], c["subsystem"],
            f"{c['mnemonic']} {c['description']} {c['opcode']} {c['subsystem']} {c['criticality']}")

    for t in bundle["telemetry"]:
        add(t["mnemonic"], "telemetry", t["mnemonic"], t["description"], t["subsystem"],
            f"{t['mnemonic']} {t['description']} {t['units']} {t['subsystem']} {t['type']}")

    for a in bundle["alerts"]:
        sub = ""
        # Best-effort subsystem from alert ID pattern
        parts = a["alert_id"].split("_")
        if len(parts) >= 2:
            sub = parts[1]
        add(a["alert_id"], "alert", a["alert_id"], a["description"], sub,
            f"{a['alert_id']} {a['description']} {a['severity']} {a['type']} {a['condition']}")

    for f in bundle["fdir"]:
        sub = ""
        parts = f["fdir_id"].split("_")
        if len(parts) >= 2:
            sub = parts[1]
        add(f["fdir_id"], "fdir", f["fdir_id"], f["title"], sub,
            f"{f['fdir_id']} {f['title']} {f['response']} {f['severity']}")

    for r in bundle["flight_rules"]:
        add(r["rule_id"], "flight_rule", r["rule_id"], r["rule_text"], r["subsystem"],
            f"{r['rule_id']} {r['rule_text']} {r['operator_action']} {r['subsystem']}")

    for p in bundle["procedures"]:
        sub = ""
        parts = p["procedure_id"].split("_")
        if len(parts) >= 2:
            sub = parts[1]
        add(p["procedure_id"], "procedure", p["procedure_id"], p["title"], sub,
            f"{p['procedure_id']} {p['title']} {p['description']} {p['type']} {p['criticality']}")

    return {
        "docs": docs,
        "tokens": {tok: sorted(ids) for tok, ids in inv.items()},
    }


def write_index(index: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "search.json"
    with open(out_path, "w") as f:
        json.dump(index, f, separators=(",", ":"))
    return out_path
