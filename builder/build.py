"""
Main build entry point.

Usage: python -m builder.build [--inputs DIR] [--out DIR]

Discovers all fsw-vX.Y/ folders under inputs/, builds a JSON bundle and
search index per version, then produces a single self-contained
index.html with all data, CSS, and JS inlined — works directly from
file:// without a server.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .resolver import build_bundle, write_bundle
from .search_index import build_index, write_index


def inline_site(out_root: Path, webapp_root: Path, manifest: dict, bundles: dict, indexes: dict):
    """
    Produce a single self-contained index.html that runs from file://.

    Strategy:
      - Read webapp/index.html, webapp/assets/style.css, webapp/assets/app.js.
      - Inline CSS into a <style> block.
      - Inline a <script> block defining window.__OPSCON_DATA__ with manifest,
        bundles, and indexes.
      - Inline app.js (which checks for __OPSCON_DATA__ and skips fetch()).
    """
    html = (webapp_root / "index.html").read_text(encoding="utf-8")
    css = (webapp_root / "assets" / "style.css").read_text(encoding="utf-8")
    js = (webapp_root / "assets" / "app.js").read_text(encoding="utf-8")

    data_blob = {
        "manifest": manifest,
        "bundles": bundles,
        "indexes": indexes,
    }
    # Use json.dumps with ensure_ascii=False for compactness; embed safely
    # by replacing </script> sequences (rare but possible).
    data_json = json.dumps(data_blob, separators=(",", ":"), ensure_ascii=False)
    data_json = data_json.replace("</script>", "<\\/script>")

    inlined_data = f"<script>window.__OPSCON_DATA__ = {data_json};</script>"
    inlined_css = f"<style>\n{css}\n</style>"
    inlined_js = f"<script>\n{js}\n</script>"

    # Replace external link/script references
    html = html.replace(
        '<link rel="stylesheet" href="assets/style.css">',
        inlined_css
    )
    html = html.replace(
        '<script src="assets/app.js"></script>',
        inlined_data + "\n" + inlined_js
    )

    (out_root / "index.html").write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default="inputs", help="Inputs root directory")
    ap.add_argument("--webapp", default="webapp", help="Static site source")
    ap.add_argument("--out", default="dist", help="Output dist directory")
    ap.add_argument("--strict", action="store_true",
                    help="Fail on unresolved references instead of warning")
    ap.add_argument("--no-inline", action="store_true",
                    help="Skip inlining data into HTML (keep multi-file layout)")
    args = ap.parse_args()

    inputs_root = Path(args.inputs).resolve()
    webapp_root = Path(args.webapp).resolve()
    out_root = Path(args.out).resolve()

    # Discover FSW versions
    versions = sorted(
        p.name.removeprefix("fsw-v")
        for p in inputs_root.iterdir()
        if p.is_dir() and p.name.startswith("fsw-v")
    )
    if not versions:
        print(f"ERROR: no fsw-vX.Y/ directories found under {inputs_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Discovered FSW versions: {', '.join(versions)}")

    # Clean out
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    # Copy static webapp into out (also keeps the non-inlined version available)
    shutil.copytree(webapp_root, out_root, dirs_exist_ok=True)

    manifest = {"versions": [], "default_version": versions[0]}
    bundles: dict[str, dict] = {}
    indexes: dict[str, dict] = {}
    total_warnings = 0

    for v in versions:
        print(f"\n--- Building FSW v{v} ---")
        bundle, warnings = build_bundle(inputs_root, v)
        for w in warnings[:10]:
            print(f"  WARN: {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")
        total_warnings += len(warnings)

        if args.strict and warnings:
            print(f"ERROR: --strict mode and {len(warnings)} unresolved references", file=sys.stderr)
            sys.exit(2)

        version_out = out_root / "data" / f"fsw-v{v}"
        write_bundle(bundle, version_out)
        index = build_index(bundle)
        write_index(index, version_out)

        bundles[v] = bundle
        indexes[v] = index

        manifest["versions"].append({
            "version": v,
            "stats": bundle["stats"],
            "subsystems": bundle["subsystems"],
            "warnings": len(warnings),
        })
        print(f"  stats: {bundle['stats']}")

    # Newest version becomes default
    manifest["default_version"] = max(versions)

    with open(out_root / "data" / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    if not args.no_inline:
        inline_site(out_root, webapp_root, manifest, bundles, indexes)
        size_mb = (out_root / "index.html").stat().st_size / (1024 * 1024)
        print(f"\nInlined index.html: {size_mb:.2f} MB (works from file:// directly)")

    print(f"\nBuild complete: {out_root}")
    print(f"Total warnings across all versions: {total_warnings}")


if __name__ == "__main__":
    main()
