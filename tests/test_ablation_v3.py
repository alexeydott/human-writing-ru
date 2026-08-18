#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts/ablate_signals_v3.py"
spec = importlib.util.spec_from_file_location("ablate_v3", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def fake_row(i: int, *, author: str, source: str = "s1", channel: str = "blog") -> dict:
    return {
        "id": f"d{i}",
        "profile": "prose",
        "author_or_group": author,
        "source_id": source,
        "channel": channel,
        "_path": f"/tmp/d{i}",
        "_calibration_eligible": True,
        "_lexical_only": False,
        "_features": {
            "words": 250,
            "sentences": 12,
            "paragraphs": 10,
            "road_per_1000": 0.0,
            "sentence_cv": 0.5,
            "sentence_max_words": 20,
            "one_sentence_paragraph_ratio": 0.2,
            "jargon_per_1000": 0.0,
            "_counts": {"road": 0, "jargon": 0},
        },
    }


def test_author_groups_do_not_cross_split() -> None:
    rows = []
    for i in range(20):
        rows.append(fake_row(i, author=f"a{i//2}"))
    split_spec = json.loads((ROOT / "benchmark/ablation/spec-v3.json").read_text(encoding="utf-8"))["split"]
    cal, val = mod.split_rows(rows, "prose", split_spec)
    ca = {r["author_or_group"] for r in cal}
    va = {r["author_or_group"] for r in val}
    assert not (ca & va), (ca & va)


def test_candidate_is_conservative() -> None:
    high = {"direction": "high", "candidate_quantile": 0.95}
    low = {"direction": "low", "candidate_quantile": 0.05}
    assert mod.candidate_threshold(10, [1, 2, 3], high) == 10
    assert mod.candidate_threshold(10, [20, 30, 40], high) > 10
    assert mod.candidate_threshold(0.3, [0.4, 0.5], low) == 0.3
    assert mod.candidate_threshold(0.3, [0.1, 0.2], low) < 0.3


def test_diversity_gate_detects_single_source() -> None:
    rows = [fake_row(i, author=f"a{i}") for i in range(50)]
    cfg = {"minimum_sources":3,"minimum_channels":1,"maximum_source_document_share":0.6,"maximum_source_word_share":0.6,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":True,"minimum_known_author_coverage":0.5,"maximum_known_author_document_share":0.5,"maximum_known_author_word_share":0.5}
    out = mod.diversity(rows, cfg)
    assert not out["gate_met"]
    assert not out["checks"]["minimum_sources"]
    assert not out["checks"]["maximum_source_document_share"]



def test_unknown_does_not_count_as_diversity() -> None:
    rows = [fake_row(i, author=f"a{i}", source="unknown", channel="unknown") for i in range(50)]
    cfg = {"minimum_sources":1,"minimum_channels":1,"maximum_source_document_share":0.8,"maximum_source_word_share":0.8,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":False,"minimum_known_author_coverage":0.0,"maximum_known_author_document_share":0.5,"maximum_known_author_word_share":0.5}
    out = mod.diversity(rows, cfg)
    assert out["known_source_count"] == 0
    assert out["known_channel_count"] == 0
    assert out["gate_met"] is False


def test_group_split_is_reasonably_balanced() -> None:
    rows = [fake_row(i, author=f"a{i}") for i in range(100)]
    split_spec = json.loads((ROOT / "benchmark/ablation/spec-v3.json").read_text(encoding="utf-8"))["split"]
    cal, val = mod.split_rows(rows, "prose", split_spec)
    assert 50 <= len(cal) <= 70, (len(cal), len(val))
    assert len(cal) + len(val) == 100


def test_signal_subset_can_fail_diversity_even_when_profile_is_diverse() -> None:
    rows=[]
    for i in range(60):
        source=f"s{(i % 3)+1}"
        channel=["blog","media","social"][i%3]
        r=fake_row(i, author=f"a{i}", source=source, channel=channel)
        # Make the road signal eligible/firing only in source s1; full profile is diverse.
        if source=="s1":
            r["_features"]["road_per_1000"]=20.0
            r["_features"]["_counts"]["road"]=5
        rows.append(r)
    cfg={"minimum_sources":3,"minimum_channels":3,"maximum_source_document_share":0.60,"maximum_source_word_share":0.60,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":True,"minimum_known_author_coverage":0.5,"maximum_known_author_document_share":0.50,"maximum_known_author_word_share":0.50}
    assert mod.diversity(rows,cfg)["gate_met"] is True
    subset=[r for r in rows if r["source_id"]=="s1"]
    assert mod.diversity(subset,cfg)["gate_met"] is False

def test_split_group_cannot_mask_shared_author() -> None:
    rows = []
    # Same author appears under two explicit split groups. A first-key strategy
    # would permit leakage; connected-components grouping must not.
    for i in range(12):
        r = fake_row(i, author="same-author", source="s1" if i < 6 else "s2")
        r["split_group"] = "g1" if i < 6 else "g2"
        r["independence_group"] = f"doc-{i}"
        rows.append(r)
    split_spec = json.loads((ROOT / "benchmark/ablation/spec-v3.json").read_text(encoding="utf-8"))["split"]
    cal, val = mod.split_rows(rows, "prose", split_spec)
    assert not ({r["author_or_group"] for r in cal} & {r["author_or_group"] for r in val})
    # All rows are one connected author component, therefore one arm may be empty;
    # the downstream split gate must reject that evidence rather than leak it.
    assert not cal or not val


def test_source_scoped_independence_ids_do_not_false_merge() -> None:
    rows=[]
    for i, source in enumerate(["s1","s2"]):
        r=fake_row(i,author=f"a{i}",source=source)
        r["independence_group"]="42"
        rows.append(r)
    split_spec=json.loads((ROOT/"benchmark/ablation/spec-v3.json").read_text(encoding="utf-8"))["split"]
    groups=mod.split_components(rows,split_spec)
    assert len(groups)==2, groups




def test_author_case_variants_cannot_cross_split() -> None:
    rows=[]
    for i, author in enumerate(["Иван Иванов", "иван   иванов"]):
        r=fake_row(i, author=author, source=f"s{i+1}")
        r["independence_group"] = f"doc-{i}"
        rows.append(r)
    split_spec=json.loads((ROOT/"benchmark/ablation/spec-v3.json").read_text(encoding="utf-8"))["split"]
    groups=mod.split_components(rows, split_spec)
    assert len(groups)==1, groups


def test_unknown_sentinels_and_case_variants_do_not_fake_diversity() -> None:
    rows=[]
    for i,(source,channel) in enumerate([("S1","BLOG"),("s1","blog"),("UNKNOWN-SOURCE","n/a")]):
        rows.append(fake_row(i, author=f"a{i}", source=source, channel=channel))
    cfg={"minimum_sources":2,"minimum_channels":2,"maximum_source_document_share":1.0,"maximum_source_word_share":1.0,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":False,"minimum_known_author_coverage":0.0,"maximum_known_author_document_share":1.0,"maximum_known_author_word_share":1.0}
    out=mod.diversity(rows,cfg)
    assert out["known_source_count"]==1
    assert out["known_channel_count"]==1
    assert out["known_source_document_coverage"] < 1.0
    assert out["gate_met"] is False


def test_unknown_source_cannot_dilute_concentration() -> None:
    rows=[]
    for i in range(10):
        source="s1" if i < 6 else "unknown"
        r=fake_row(i,author=f"a{i}",source=source,channel="blog" if i<6 else "unknown")
        rows.append(r)
    cfg={"minimum_sources":1,"minimum_channels":1,"maximum_source_document_share":0.8,"maximum_source_word_share":0.8,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":False,"minimum_known_author_coverage":0.0,"maximum_known_author_document_share":1.0,"maximum_known_author_word_share":1.0}
    out=mod.diversity(rows,cfg)
    assert out["maximum_source_document_share_observed"]==1.0
    assert out["known_source_document_coverage"]==0.6
    assert out["gate_met"] is False


def test_word_mass_concentration_is_gated() -> None:
    rows=[]
    for i in range(10):
        source="s1" if i < 5 else "s2"
        r=fake_row(i,author=f"a{i}",source=source,channel="blog")
        r["_features"]["words"] = 1000 if source=="s1" else 100
        rows.append(r)
    cfg={"minimum_sources":2,"minimum_channels":1,"maximum_source_document_share":0.6,"maximum_source_word_share":0.6,"minimum_known_source_coverage":1.0,"minimum_known_channel_coverage":1.0,"author_concentration_required":False,"minimum_known_author_coverage":0.0,"maximum_known_author_document_share":1.0,"maximum_known_author_word_share":1.0}
    out=mod.diversity(rows,cfg)
    assert out["maximum_source_document_share_observed"]==0.5
    assert out["maximum_source_word_share_observed"] > 0.9
    assert out["checks"]["maximum_source_document_share"] is True
    assert out["checks"]["maximum_source_word_share"] is False


def test_conflicting_duplicate_annotations_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.csv"
        p.write_text("document_id,signal,label\nd1,long-sentence,actionable\nd1,long-sentence,non_actionable\n",encoding="utf-8")
        try:
            mod.load_annotations(p)
        except SystemExit as exc:
            assert "conflicting duplicate annotation" in str(exc)
        else:
            raise AssertionError("conflicting duplicate annotation was accepted")


def test_blank_annotation_template_rows_are_ignored() -> None:
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.csv"
        p.write_text("document_id,signal,label\nd1,long-sentence,\n",encoding="utf-8")
        assert mod.load_annotations(p)=={}



def test_uncertain_annotations_do_not_count_as_decisive_evidence() -> None:
    rows=[fake_row(i,author=f"a{i}") for i in range(20)]
    annotations={(r["id"],"long-sentence"):"uncertain" for r in rows}
    out=mod.annotation_summary(rows,"long-sentence",annotations)
    assert out["annotated"]==20
    assert out["decisive"]==0
    assert out["uncertain"]==20
    assert out["actionable_precision"] is None





def test_v3_runner_rejects_sha_mismatch_and_exact_duplicates() -> None:
    import hashlib
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        body="Один и тот же проверочный русский текст для контроля целостности.\n"
        (d/"a.txt").write_text(body,encoding="utf-8")
        (d/"b.txt").write_text(body,encoding="utf-8")
        manifest=d/"manifest.csv"; output=d/"out.json"
        manifest.write_text(
            "id,path,profile,channel,source_id,sha256\n"
            "a,a.txt,prose,blog,s1,deadbeef\n",encoding="utf-8")
        proc=subprocess.run([sys.executable,str(MOD_PATH),"--manifest",str(manifest),"--output",str(output)],cwd=ROOT,text=True,capture_output=True)
        assert proc.returncode!=0 and "sha256 mismatch" in (proc.stdout+proc.stderr)
        digest=hashlib.sha256(body.encode("utf-8")).hexdigest()
        manifest.write_text(
            "id,path,profile,channel,source_id,sha256\n"
            f"a,a.txt,prose,blog,s1,{digest}\n"
            f"b,b.txt,prose,blog,s2,{digest}\n",encoding="utf-8")
        proc=subprocess.run([sys.executable,str(MOD_PATH),"--manifest",str(manifest),"--output",str(output)],cwd=ROOT,text=True,capture_output=True)
        assert proc.returncode!=0 and "exact duplicate text" in (proc.stdout+proc.stderr)


def test_v3_runner_rejects_duplicate_document_ids() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "a.txt").write_text("Первый проверочный русский документ.\n", encoding="utf-8")
        (d / "b.txt").write_text("Второй проверочный русский документ.\n", encoding="utf-8")
        manifest = d / "manifest.csv"
        manifest.write_text(
            "id,path,profile,channel,source_id,author_or_group,calibration_eligible,lexical_only\n"
            "dup,a.txt,prose,blog,s1,a1,1,0\n"
            "dup,b.txt,prose,blog,s2,a2,1,0\n", encoding="utf-8"
        )
        output = d / "out.json"
        p = subprocess.run([sys.executable, str(MOD_PATH), "--manifest", str(manifest), "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
        assert p.returncode != 0
        assert "duplicate document id" in (p.stderr + p.stdout)
        assert not output.exists()


def test_v3_runner_rejects_unknown_annotation_references() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "one.txt").write_text("Это проверочный русский документ для аннотации.\n", encoding="utf-8")
        manifest = d / "manifest.csv"
        manifest.write_text(
            "id,path,profile,channel,source_id,author_or_group,calibration_eligible,lexical_only\n"
            "one,one.txt,prose,blog,s1,a1,1,0\n", encoding="utf-8"
        )
        annotations = d / "annotations.csv"
        annotations.write_text("document_id,signal,label\nmissing,long-sentence,actionable\n", encoding="utf-8")
        output = d / "out.json"
        p = subprocess.run([sys.executable, str(MOD_PATH), "--manifest", str(manifest), "--output", str(output), "--annotations", str(annotations)], cwd=ROOT, text=True, capture_output=True)
        assert p.returncode != 0
        assert "unknown document/signal" in (p.stderr + p.stdout)
        assert not output.exists()


def test_cli_blocks_decision_on_small_manifest() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        text = d / "one.txt"
        text.write_text("Это небольшой нормальный русский текст. Он нужен только для проверки ворот качества.\n", encoding="utf-8")
        manifest = d / "manifest.csv"
        manifest.write_text(
            "id,path,profile,channel,source_id,author_or_group,calibration_eligible,lexical_only\n"
            "one,one.txt,prose,blog,s1,a1,1,0\n",
            encoding="utf-8",
        )
        output = d / "out.json"
        annotation_template = d / "annotations.csv"
        p = subprocess.run(
            [sys.executable, str(MOD_PATH), "--manifest", str(manifest), "--output", str(output), "--annotation-template", str(annotation_template)],
            cwd=ROOT, text=True, capture_output=True,
        )
        assert p.returncode == 0, p.stderr
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["global"]["all_profile_gates_met"] is False
        assert data["global"]["automatic_policy_update_allowed"] is False
        assert data["signals"]["long-sentence"]["profiles"]["prose"]["candidate_decision"] == "blocked_evidence_gate_not_met"
        assert annotation_template.exists()
        template_lines = annotation_template.read_text(encoding="utf-8").splitlines()
        assert template_lines[0].startswith("document_id,signal,profile")
        assert len(template_lines) == 1  # no review burden before evidence gates pass


def main() -> None:
    test_author_groups_do_not_cross_split()
    test_candidate_is_conservative()
    test_diversity_gate_detects_single_source()
    test_unknown_does_not_count_as_diversity()
    test_group_split_is_reasonably_balanced()
    test_signal_subset_can_fail_diversity_even_when_profile_is_diverse()
    test_split_group_cannot_mask_shared_author()
    test_source_scoped_independence_ids_do_not_false_merge()
    test_author_case_variants_cannot_cross_split()
    test_unknown_sentinels_and_case_variants_do_not_fake_diversity()
    test_unknown_source_cannot_dilute_concentration()
    test_word_mass_concentration_is_gated()
    test_conflicting_duplicate_annotations_are_rejected()
    test_blank_annotation_template_rows_are_ignored()
    test_uncertain_annotations_do_not_count_as_decisive_evidence()
    test_v3_runner_rejects_sha_mismatch_and_exact_duplicates()
    test_v3_runner_rejects_duplicate_document_ids()
    test_v3_runner_rejects_unknown_annotation_references()
    test_cli_blocks_decision_on_small_manifest()
    print("test_ablation_v3: OK")


if __name__ == "__main__":
    main()
