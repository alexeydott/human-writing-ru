#!/usr/bin/env python3
"""Validate materialized external held-out data before five-signal ablation.

This script checks file integrity, exact/near duplicates, document/word freeze
counts, channel coverage and per-signal sample eligibility. It does not change
linter code or thresholds.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_prose_ru as cp

SPEC = ROOT / "benchmark/ablation/spec-v3.json"
PROFILE_FILE = ROOT / "profiles/editorial-baseline.json"
TOKEN_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+(?:[-'][А-Яа-яЁёA-Za-z]+)*")



UNKNOWN_PROVENANCE = {"", "unknown", "unknown-source", "n/a", "na", "none", "null", "?"}

def normalize_provenance(value: str | None) -> str | None:
    """Normalize human-readable provenance labels for diagnostics only.

    Opaque document/split identifiers remain untouched elsewhere. Missing and
    sentinel values never count as source/channel/author diversity.
    """
    if value is None:
        return None
    normalized = " ".join(str(value).split()).casefold()
    return None if normalized in UNKNOWN_PROVENANCE else normalized

def truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _stable_shingle(value: str) -> bytes:
    # Stable across Python processes/runs; unlike built-in hash(), this keeps
    # near-copy clustering reproducible between machines.
    return hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()


def shingles(text: str, n: int = 5, cap: int = 2500) -> set[bytes]:
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    if len(toks) < n:
        return {_stable_shingle(" ".join(toks))} if toks else set()
    seq = toks
    step = max(1, (len(seq) - n + 1) // cap)
    return {_stable_shingle(" ".join(seq[i:i+n])) for i in range(0, len(seq) - n + 1, step)}


def jaccard(a: set[bytes], b: set[bytes]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class DSU:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))
    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a




def normalized_profile_gate(spec: dict) -> dict:
    """Return the profile-size gate in one stable shape.

    Decision protocol v3 calls this ``profile_gate``. Historical benchmark
    fixtures used ``freeze_gate`` with longer key names. Accepting both keeps
    the validator useful for archived regression fixtures without letting the
    operational default drift away from the current protocol.
    """
    if "profile_gate" in spec:
        gate = spec["profile_gate"]
        return {
            "minimum_independent_documents": int(gate["minimum_independent_documents"]),
            "minimum_words": int(gate["minimum_words"]),
            "source_key": "profile_gate",
        }
    if "freeze_gate" in spec:
        gate = spec["freeze_gate"]
        return {
            "minimum_independent_documents": int(gate["minimum_independent_documents_per_profile"]),
            "minimum_words": int(gate["minimum_words_per_profile"]),
            "source_key": "freeze_gate",
        }
    raise SystemExit("spec must contain profile_gate (v3) or historical freeze_gate")

def signal_eligible(features: dict, profile: dict, ss: dict) -> bool:
    if ss.get("requires_rhythm_checks") and not profile.get("rhythm_checks", True):
        return False
    size_key = ss.get("minimum_size_key")
    size_feature = ss.get("minimum_size_feature")
    if size_key and size_feature and features.get(size_feature, 0) < profile.get(size_key, 0):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate external held-out materialization")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--profile-file", type=Path, default=PROFILE_FILE)
    ap.add_argument("--near-duplicate-threshold", type=float, default=0.92,
                    help="Research heuristic for obvious repost/near-copy clustering; not a language norm")
    ap.add_argument("--validated-manifest", type=Path, default=None,
                    help="Write deduplicated representative manifest for the current decision protocol; default: manifest.validated.csv next to input")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    profiles = cp.load_profiles(args.profile_file)
    size_gate = normalized_profile_gate(spec)
    freeze_docs = size_gate["minimum_independent_documents"]
    freeze_words = size_gate["minimum_words"]
    base = args.manifest.parent

    with args.manifest.open(encoding="utf-8", newline="") as manifest_handle:
        manifest_reader = csv.DictReader(manifest_handle)
        input_fieldnames = list(manifest_reader.fieldnames or [])
        raw_rows = list(manifest_reader)
    required_manifest_fields = {"id", "path", "profile"}
    missing_fields = sorted(required_manifest_fields - set(input_fieldnames))
    if missing_fields:
        raise SystemExit("manifest missing required fields: " + ", ".join(missing_fields))
    id_counts = Counter((row.get("id") or "").strip() for row in raw_rows)
    duplicate_ids = {doc_id for doc_id, count in id_counts.items() if doc_id and count > 1}
    docs = []
    invalid = []
    exact_hash_to_indexes: dict[str, list[int]] = defaultdict(list)
    for row in raw_rows:
        doc_id = (row.get("id") or "").strip()
        if not doc_id:
            invalid.append({"id": "", "reason": "missing_id", "path": row.get("path", "")})
            continue
        if doc_id in duplicate_ids:
            invalid.append({"id": doc_id, "reason": "duplicate_id", "path": row.get("path", "")})
            continue
        p = Path(row.get("path") or "")
        if not p.is_absolute():
            p = (base / p).resolve()
        if not p.exists():
            invalid.append({"id": row.get("id", ""), "reason": "missing_file", "path": str(p)})
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except Exception as exc:
            invalid.append({"id": row.get("id", ""), "reason": f"utf8_error:{exc}", "path": str(p)})
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if row.get("sha256") and row["sha256"] != digest:
            invalid.append({"id": row.get("id", ""), "reason": "sha256_mismatch", "path": str(p)})
            continue
        profile_name = row.get("profile", "")
        if profile_name not in profiles:
            invalid.append({"id": row.get("id", ""), "reason": f"unknown_profile:{profile_name}", "path": str(p)})
            continue
        features = cp.compute_features(text, include_quotes=False)
        idx = len(docs)
        docs.append({"row": row, "path": str(p), "text": text, "sha256": digest, "features": features})
        exact_hash_to_indexes[digest].append(idx)

    # Exact copies within one profile belong to one independence cluster.
    # If identical text is routed to different profiles, silently choosing one
    # representative would make profile counts depend on arbitrary sort/order.
    # Treat that as a routing conflict and exclude every ambiguous copy.
    dsu = DSU(len(docs))
    exact_groups = []
    cross_profile_exact_duplicate_groups = []
    ambiguous_exact_indexes: set[int] = set()
    for digest, indexes in exact_hash_to_indexes.items():
        if len(indexes) > 1:
            ids = [docs[i]["row"].get("id", str(i)) for i in indexes]
            profiles_in_group = sorted({docs[i]["row"].get("profile", "") for i in indexes})
            exact_groups.append(ids)
            if len(profiles_in_group) > 1:
                cross_profile_exact_duplicate_groups.append({
                    "sha256": digest, "profiles": profiles_in_group, "document_ids": ids
                })
                ambiguous_exact_indexes.update(indexes)
                for i in indexes:
                    invalid.append({
                        "id": docs[i]["row"].get("id", str(i)),
                        "reason": "cross_profile_exact_duplicate",
                        "path": docs[i]["path"],
                        "profiles": profiles_in_group,
                    })
                continue
            for i in indexes[1:]:
                dsu.union(indexes[0], i)

    # Explicit source-document/independence identifiers are source-scoped.
    # Different corpora frequently reuse simple IDs such as "1" or "001"; a
    # global key would falsely collapse unrelated documents. Exact/near-copy
    # clustering still catches genuine cross-source duplicates independently.
    by_independence = defaultdict(list)
    for i, doc in enumerate(docs):
        if i in ambiguous_exact_indexes:
            continue
        row = doc["row"]
        source = (row.get("source_id") or row.get("corpus") or "unknown-source").strip()
        marker = (row.get("source_document_id") or row.get("independence_group") or row.get("id") or str(i)).strip()
        key = (source, marker)
        by_independence[key].append(i)
    for indexes in by_independence.values():
        for i in indexes[1:]:
            dsu.union(indexes[0], i)

    # Conservative near-copy clustering: compare only documents within the same
    # profile. Threshold 0.92 is a benchmark heuristic for obvious reposts, not
    # a stylistic or linguistic threshold.
    sh = [shingles(d["text"]) for d in docs]
    near_pairs = []
    for i in range(len(docs)):
        if i in ambiguous_exact_indexes:
            continue
        for j in range(i + 1, len(docs)):
            if j in ambiguous_exact_indexes:
                continue
            if docs[i]["row"].get("profile") != docs[j]["row"].get("profile"):
                continue
            # Cheap size guard before Jaccard.
            wi = int(docs[i]["features"].get("words", 0))
            wj = int(docs[j]["features"].get("words", 0))
            if min(wi, wj) and max(wi, wj) / min(wi, wj) > 1.35:
                continue
            sim = jaccard(sh[i], sh[j])
            if sim >= args.near_duplicate_threshold:
                near_pairs.append({
                    "a": docs[i]["row"].get("id", str(i)),
                    "b": docs[j]["row"].get("id", str(j)),
                    "jaccard": round(sim, 4),
                })
                dsu.union(i, j)

    clusters = defaultdict(list)
    for i in range(len(docs)):
        clusters[dsu.find(i)].append(i)

    # A cluster contributes one document and one representative's words to the
    # freeze count. Pick the longest representative so repost duplication cannot
    # increase either document or word totals.
    reps = []
    for indexes in clusters.values():
        if any(i in ambiguous_exact_indexes for i in indexes):
            continue
        rep = max(indexes, key=lambda i: int(docs[i]["features"].get("words", 0)))
        reps.append(rep)
    reps.sort(key=lambda i: (docs[i]["row"].get("profile", ""), docs[i]["row"].get("id", "")))

    # The decision runner consumes a representative-only manifest. Therefore
    # validation must emit one; feeding the raw acquisition manifest directly to
    # any threshold analysis could inflate both sample counts and quantiles.
    validated_manifest = args.validated_manifest or args.manifest.with_name("manifest.validated.csv")
    validated_manifest.parent.mkdir(parents=True, exist_ok=True)
    representative_rows = []
    for i in reps:
        row = dict(docs[i]["row"])
        # Relative paths in the input manifest are relative to the input manifest,
        # not necessarily to a custom validated-manifest destination. Rebase them
        # so the decision runner resolves exactly the files that were validated.
        row["path"] = os.path.relpath(docs[i]["path"], validated_manifest.parent)
        representative_rows.append(row)
    fieldnames = list(raw_rows[0].keys()) if raw_rows else (input_fieldnames or ["id", "path", "profile"])
    with validated_manifest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(representative_rows)
    validated_manifest_sha256 = hashlib.sha256(validated_manifest.read_bytes()).hexdigest()

    profile_stats = {}
    for profile_name, pcfg in profiles.items():
        indexes = [i for i in reps if docs[i]["row"].get("profile") == profile_name and truthy(docs[i]["row"].get("calibration_eligible"), True)]
        words = sum(int(docs[i]["features"].get("words", 0)) for i in indexes)
        channel_values = [normalize_provenance(docs[i]["row"].get("channel")) for i in indexes]
        author_values = [normalize_provenance(docs[i]["row"].get("author_or_group")) for i in indexes]
        source_values = [normalize_provenance(docs[i]["row"].get("source_id")) for i in indexes]
        channels = Counter(v for v in channel_values if v is not None)
        authors = Counter(v for v in author_values if v is not None)
        sources = Counter(v for v in source_values if v is not None)
        signal_counts = {}
        for signal, ss in spec["signals"].items():
            eligible_idx = [i for i in indexes if signal_eligible(docs[i]["features"], pcfg, ss)]
            signal_counts[signal] = {
                "eligible_documents": len(eligible_idx),
                "eligible_words": sum(int(docs[i]["features"].get("words", 0)) for i in eligible_idx),
            }
        known_authors = authors
        top_author, top_author_count = known_authors.most_common(1)[0] if known_authors else (None, 0)
        top_source, top_source_count = sources.most_common(1)[0] if sources else (None, 0)
        known_author_documents = sum(known_authors.values())
        known_source_documents = sum(sources.values())
        known_channel_documents = sum(channels.values())
        profile_stats[profile_name] = {
            "independent_documents": len(indexes),
            "independent_words": words,
            "freeze_gate_met": len(indexes) >= freeze_docs and words >= freeze_words,
            "channels": dict(channels),
            "sources": dict(sources),
            "known_channel_documents": known_channel_documents,
            "known_channel_document_coverage": round(known_channel_documents / len(indexes), 4) if indexes else 0.0,
            "known_source_documents": known_source_documents,
            "known_source_document_coverage": round(known_source_documents / len(indexes), 4) if indexes else 0.0,
            "largest_source_share_of_all_documents": round(top_source_count / len(indexes), 4) if indexes and top_source else None,
            "largest_source_share_of_known_documents": round(top_source_count / known_source_documents, 4) if known_source_documents and top_source else None,
            # Historical alias: denominator is all profile documents.
            "largest_source_share": round(top_source_count / len(indexes), 4) if indexes and top_source else 0.0,
            "largest_source": top_source,
            "known_author_documents": known_author_documents,
            "known_author_document_coverage": round(known_author_documents / len(indexes), 4) if indexes else 0.0,
            "distinct_known_author_groups": len(known_authors),
            "largest_known_author_share_of_all_documents": round(top_author_count / len(indexes), 4) if indexes and top_author else None,
            "largest_known_author_share_of_known_documents": round(top_author_count / known_author_documents, 4) if known_author_documents and top_author else None,
            # Historical aliases retained for readers of older reports.
            "known_author_groups": known_author_documents,
            "largest_known_author_share": round(top_author_count / len(indexes), 4) if indexes and top_author else None,
            "largest_known_author": top_author,
            "signal_sample_eligibility": signal_counts,
        }

    required_profiles = tuple(sorted(profiles))
    validation_clean = not invalid and not cross_profile_exact_duplicate_groups
    profile_size_ready = all(profile_stats[p]["freeze_gate_met"] for p in required_profiles)
    report = {
        "schema_version": 1,
        "status": "external_heldout_validation",
        "manifest": str(args.manifest),
        "gate_spec": str(args.spec),
        "profile_size_gate": {
            "minimum_independent_documents": freeze_docs,
            "minimum_words": freeze_words,
            "source_key": size_gate["source_key"],
        },
        # Compatibility name for archived report consumers; values are normalized
        # and are not a second independent gate.
        "freeze_gate": {
            "minimum_independent_documents_per_profile": freeze_docs,
            "minimum_words_per_profile": freeze_words,
        },
        "near_duplicate_threshold": args.near_duplicate_threshold,
        "near_duplicate_note": "High-similarity repost heuristic for benchmark independence only; not a Russian-language norm.",
        "manifest_rows": len(raw_rows),
        "valid_files": len(docs),
        "validated_representative_manifest": str(validated_manifest),
        "validated_representative_manifest_sha256": validated_manifest_sha256,
        "validated_representative_rows": len(representative_rows),
        "decision_input_note": "Use validated_representative_manifest as input to the current decision protocol; never use the raw acquisition manifest for threshold decisions.",
        "invalid_files": invalid,
        "validation_clean": validation_clean,
        "independence_clusters": len([idx for idx in clusters.values() if not any(i in ambiguous_exact_indexes for i in idx)]),
        "exact_duplicate_groups": exact_groups,
        "cross_profile_exact_duplicate_groups": cross_profile_exact_duplicate_groups,
        "near_duplicate_pairs": near_pairs,
        "profiles": profile_stats,
        "required_profiles_for_freeze": list(required_profiles),
        "ready_for_profile_freeze_stage": validation_clean and profile_size_ready,
        "ready_for_decision_protocol_input": validation_clean and profile_size_ready,
        "ready_for_unchanged_ablation": validation_clean and profile_size_ready,
        "ready_for_unchanged_ablation_note": "Deprecated compatibility alias. It means only the historical 50/10000 profile-size stage passed; it does not satisfy v3 diversity/signal/split/adjudication evidence gates.",
        "routing_note": "social/blog/media stay as channel strata under profile=prose; the linter profile set is unchanged in this pass.",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"valid={len(docs)} clusters={len(clusters)} output={args.output}")
    print(f"validated_manifest={validated_manifest} rows={len(representative_rows)}")
    for p in required_profiles:
        s = profile_stats[p]
        print(f"{p}: docs={s['independent_documents']} words={s['independent_words']} freeze={s['freeze_gate_met']}")
    return 0 if not invalid else 2


if __name__ == "__main__":
    raise SystemExit(main())
