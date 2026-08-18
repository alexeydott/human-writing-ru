#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_external_heldout_gate.py"

# A reference-only source intentionally materializes zero documents. The gate
# runner must still run the validator, emit a validated manifest, refuse to call
# decision protocol v3, and preserve all frozen inputs.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    registry = base / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": 1,
        "sources": [{
            "id": "empty_fixture", "priority": 1,
            "profiles": ["prose"], "channels": ["fixture"],
            "adapter": "manual_reference_only", "source_url": "fixture",
            "license_or_terms": "own-test", "redistribution": "test-only",
            "target_documents": 1, "target_words": 1,
            "minimum_words_per_document": 1, "minimum_paragraphs_per_document": 1,
        }]
    }, ensure_ascii=False), encoding="utf-8")
    out = base / "heldout"
    out.mkdir()
    # Fresh mode must discard a stale manifest from an earlier source selection.
    (out / "stale.txt").write_text("Старый документ не должен попасть в новый запуск.\n", encoding="utf-8")
    (out / "manifest.csv").write_text(
        "id,path,profile,channel,source_id,calibration_eligible,lexical_only\n"
        "stale,stale.txt,prose,blog,old_source,1,0\n", encoding="utf-8"
    )
    p = subprocess.run([
        sys.executable, str(RUNNER), "--output-dir", str(out),
        "--registry", str(registry), "--sources", "empty_fixture",
        "--timeout", "1", "--delay", "0", "--max-index-pages", "1",
    ], cwd=ROOT, text=True, capture_output=True)
    assert p.returncode == 3, (p.returncode, p.stdout, p.stderr)
    assert (out / "manifest.csv").exists()
    assert (out / "manifest.validated.csv").exists()
    header = (out / "manifest.validated.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "channel" in header and "sha256" in header and "calibration_eligible" in header
    assert (out / "VALIDATION_REPORT.json").exists()
    assert (out / "DECISION_NOT_RUN.json").exists()
    assert not (out / "ABLATION_DECISION_V3.json").exists()
    report = json.loads((out / "NETWORK_GATE_RUN_REPORT.json").read_text(encoding="utf-8"))
    assert report["status"] == "profile_freeze_stage_not_met_decision_v3_blocked"
    assert report["workspace_mode"] == "fresh"
    assert "stale" not in (out / "manifest.csv").read_text(encoding="utf-8")
    assert report["frozen_inputs_pre"]["ok"] is True
    assert report["frozen_inputs_post_acquisition"]["ok"] is True
    validation = json.loads((out / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    assert validation["validated_representative_rows"] == 0
    assert validation["ready_for_profile_freeze_stage"] is False

# Explicit resume must reject manifests carrying source IDs outside the selected set.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    registry = base / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": 1,
        "sources": [{
            "id": "empty_fixture", "profiles": ["prose"], "channels": ["fixture"],
            "adapter": "manual_reference_only", "source_url": "fixture",
            "redistribution": "test-only", "status": "catalogued"
        }]
    }), encoding="utf-8")
    out = base / "heldout"; out.mkdir()
    (out / "manifest.csv").write_text(
        "id,path,profile,channel,source_id\nold,old.txt,prose,blog,other_source\n", encoding="utf-8"
    )
    p = subprocess.run([
        sys.executable, str(RUNNER), "--output-dir", str(out), "--registry", str(registry),
        "--sources", "empty_fixture", "--resume",
    ], cwd=ROOT, text=True, capture_output=True)
    assert p.returncode != 0
    assert "outside --sources" in (p.stdout + p.stderr)

print("OK external network gate blocking")

# A prepared data/<source_id>/manifest.csv tree is discovered without
# repeating three --local-source arguments in every local workflow command.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    local_root = base / "data"
    local = local_root / "local_fixture"
    local.mkdir(parents=True)
    body = ("Это естественно ограниченный русский документ локального корпуса. " * 30).strip()
    (local / "document.txt").write_text(body + "\n", encoding="utf-8")
    (local / "manifest.csv").write_text(
        "id,path,author_or_group,source_document_id,independence_group,channel\n"
        "local-1,document.txt,author-1,upstream-1,event-1,social\n",
        encoding="utf-8",
    )
    registry = base / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": 1,
        "sources": [{
            "id": "local_fixture", "priority": 1,
            "profiles": ["prose"], "channels": ["social"],
            "adapter": "manual_or_local_tree", "source_url": "fixture",
            "license_or_terms": "own-test", "redistribution": "test-only",
            "target_documents": 1, "target_words": 1,
            "minimum_words_per_document": 5, "minimum_paragraphs_per_document": 1,
            "status": "catalogued",
        }],
    }), encoding="utf-8")
    out = base / "heldout"
    p = subprocess.run([
        sys.executable, str(RUNNER), "--output-dir", str(out),
        "--registry", str(registry), "--sources", "local_fixture",
        "--local-corpus-root", str(local_root),
        "--timeout", "1", "--delay", "0", "--max-index-pages", "1",
    ], cwd=ROOT, text=True, capture_output=True)
    assert p.returncode == 3, (p.returncode, p.stdout, p.stderr)
    rows = (out / "manifest.csv").read_text(encoding="utf-8")
    assert "local_fixture" in rows and "author-1" in rows
    report = json.loads((out / "NETWORK_GATE_RUN_REPORT.json").read_text(encoding="utf-8"))
    assert report["local_sources"]["local_fixture"] == str(local.resolve())

print("OK local corpus auto-discovery")
