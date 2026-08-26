#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import csv
import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
from build_lite import MAX_LITE_CHARACTERS, render_lite, validate_lite

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
warnings: list[str] = []


def err(message: str) -> None:
    errors.append(message)


def warn(message: str) -> None:
    warnings.append(message)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return None


def parse_skill_frontmatter(text: str) -> tuple[dict, str] | tuple[None, None]:
    if not text.startswith("---\n"):
        err("SKILL.md frontmatter missing")
        return None, None
    end = text.find("\n---\n", 4)
    if end < 0:
        err("SKILL.md frontmatter closing delimiter missing")
        return None, None
    raw = text[4:end]
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        err(f"SKILL.md invalid YAML frontmatter: {exc}")
        return None, None
    if not isinstance(data, dict):
        err("SKILL.md frontmatter must be a mapping")
        return None, None
    return data, text[end + 5 :]


# Package hygiene first: validation itself must not leave artifacts inside the skill.
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT)
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        err(f"generated artifact: {rel}")
    if path.is_symlink():
        warn(f"symlink in package: {rel}")

version_path = ROOT / "VERSION"
version = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else ""
if not version:
    err("VERSION missing or empty")

skill_path = ROOT / "SKILL.md"
frontmatter = None
if not skill_path.exists():
    err("SKILL.md missing")
else:
    skill_text = skill_path.read_text(encoding="utf-8")
    parsed = parse_skill_frontmatter(skill_text)
    if parsed[0] is not None:
        frontmatter, body = parsed
        allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
        unknown = sorted(set(frontmatter) - allowed)
        if unknown:
            warn("unknown SKILL.md frontmatter fields: " + ", ".join(unknown))

        name = frontmatter.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            err("invalid skill name")
        elif ROOT.name != name:
            err(f"skill name must match parent directory: name={name!r} parent={ROOT.name!r}")

        description = frontmatter.get("description")
        if not isinstance(description, str) or not description.strip():
            err("description missing/empty")
        elif len(description) > 1024:
            err("description >1024 chars")

        license_value = frontmatter.get("license")
        if license_value is not None and (not isinstance(license_value, str) or not license_value.strip()):
            err("license must be a non-empty string")

        compatibility = frontmatter.get("compatibility")
        if compatibility is not None:
            if not isinstance(compatibility, str) or not compatibility.strip():
                err("compatibility must be a non-empty string")
            elif len(compatibility) > 500:
                err("compatibility >500 chars")

        metadata = frontmatter.get("metadata", {})
        if not isinstance(metadata, dict):
            err("metadata must be a mapping")
        else:
            for k, v in metadata.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    err("metadata keys and values must be strings")
            if version and metadata.get("version") != version:
                err(f"metadata.version != VERSION: {metadata.get('version')!r} != {version!r}")
            if not metadata.get("policy_version"):
                err("metadata.policy_version missing")

        if skill_text.count("\n") + 1 > 500:
            err("SKILL.md >500 lines")
        if len(skill_text.split()) > 7000:
            warn("SKILL.md is large; progressive disclosure may be weakened")

        # Backtick resource references from the main skill must exist.
        refs = sorted(set(re.findall(r"`((?:references|scripts|profiles|evals|benchmark)/[^`\s]+)`", skill_text)))
        for rel in refs:
            if not (ROOT / rel).exists():
                err(f"missing referenced file: {rel}")

# Dev/agent-context catalogs are never part of the package (see the exclusion lists in
# scripts/build_release.py); exclude them from Markdown scans so a local AI setup does not
# fail package validation because of third-party skill templates or node_modules docs.
MD_SKIP_TOP_DIRS = {
    ".git", ".agents", ".ai-factory", ".claude", ".codex", ".opencode", ".qwen", ".venv",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


def md_scan_skip(md: Path) -> bool:
    parts = md.relative_to(ROOT).parts
    if "node_modules" in parts or parts[0] in MD_SKIP_TOP_DIRS:
        return True
    if len(parts) >= 2 and parts[:2] == (".github", "skills"):
        return True
    return False


# Literal escaped newlines in prose documents are almost always packaging/editing defects.
for md in ROOT.rglob("*.md"):
    if md_scan_skip(md):
        continue
    text = md.read_text(encoding="utf-8")
    if re.search(r"(?:^|\s)\\n(?:\\n|\s)", text):
        err(f"literal escaped newline sequence in Markdown: {md.relative_to(ROOT)}")

# Validate relative Markdown links to packaged files. Ignore anchors and URLs.
link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
for md in ROOT.rglob("*.md"):
    if md_scan_skip(md):
        continue
    text = md.read_text(encoding="utf-8")
    for target in link_re.findall(text):
        target = target.strip().split("#", 1)[0]
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        candidate = (md.parent / target).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            err(f"Markdown link escapes skill root: {md.relative_to(ROOT)} -> {target}")
            continue
        if not candidate.exists():
            err(f"broken Markdown link: {md.relative_to(ROOT)} -> {target}")

# Compile Python outside the package to keep the package clean.
with tempfile.TemporaryDirectory() as temp_dir:
    temp_root = Path(temp_dir)
    for folder in ("scripts", "tests"):
        for py_file in (ROOT / folder).glob("*.py"):
            try:
                py_compile.compile(
                    str(py_file),
                    cfile=str(temp_root / f"{folder}-{py_file.stem}.pyc"),
                    doraise=True,
                )
            except Exception as exc:
                err(f"Python syntax {py_file.relative_to(ROOT)}: {exc}")

# Validate all JSON recursively, not only selected top-level directories.
json_cache: dict[Path, object] = {}
for jf in ROOT.rglob("*.json"):
    data = read_json(jf)
    if data is not None:
        json_cache[jf] = data

# YAML resources.
for yf in list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml")):
    try:
        yaml.safe_load(yf.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"invalid YAML {yf.relative_to(ROOT)}: {exc}")

# IDs used as keys in evaluation/source registries must be unique.
for rel, container_key, id_key in [
    ("evals/evals.json", "evals", "id"),
    ("evals/eval_queries.json", None, "id"),
    ("evals/train_queries.json", None, "id"),
    ("evals/validation_queries.json", None, "id"),
    ("benchmark/external-heldout/SOURCE_REGISTRY.json", "sources", "id"),
]:
    p = ROOT / rel
    if not p.exists():
        continue
    data = json_cache.get(p)
    if data is None:
        continue
    items = data.get(container_key, []) if container_key and isinstance(data, dict) else data
    if isinstance(items, dict) and "cases" in items:
        items = items["cases"]
    if isinstance(items, list):
        ids = [x.get(id_key) for x in items if isinstance(x, dict) and x.get(id_key)]
        duplicates = sorted({x for x in ids if ids.count(x) > 1})
        if duplicates:
            err(f"duplicate IDs in {rel}: {duplicates}")

# Frozen-input integrity: these files may only change through an explicit policy-version bump.
frozen_path = ROOT / "benchmark/external-heldout/FROZEN_INPUT_SHA256.json"
if frozen_path.exists():
    frozen = json_cache.get(frozen_path)
    if isinstance(frozen, dict):
        mapping = frozen.get("sha256", {})
        if isinstance(mapping, dict):
            for rel, expected in mapping.items():
                p = ROOT / rel
                if not p.exists():
                    err(f"frozen input missing: {rel}")
                    continue
                actual = hashlib.sha256(p.read_bytes()).hexdigest()
                if actual != expected:
                    err(f"frozen input hash mismatch: {rel}")

# Current release-integrity snapshot is generated by build_release.py and must
# describe the bytes that are actually present, not a previous candidate.
current_integrity_path = ROOT / "quality/RELEASE_INTEGRITY.json"
if not current_integrity_path.exists():
    err("quality/RELEASE_INTEGRITY.json missing")
else:
    current_integrity = json_cache.get(current_integrity_path)
    if isinstance(current_integrity, dict):
        if current_integrity.get("package_version") != version:
            err("quality/RELEASE_INTEGRITY package_version != VERSION")
        if current_integrity.get("skill_root") != ROOT.name:
            err("quality/RELEASE_INTEGRITY skill_root != parent directory")
        if current_integrity.get("frozen_inputs_match") is not True:
            err("quality/RELEASE_INTEGRITY reports frozen_inputs_match != true")
        tracked = current_integrity.get("tracked_sha256", {})
        if not isinstance(tracked, dict) or not tracked:
            err("quality/RELEASE_INTEGRITY tracked_sha256 missing/empty")
        else:
            for rel, expected in tracked.items():
                path = ROOT / rel
                if not path.exists():
                    err(f"quality/RELEASE_INTEGRITY tracked file missing: {rel}")
                    continue
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != expected:
                    err(f"quality/RELEASE_INTEGRITY stale tracked hash: {rel}")

# Current-facing docs should identify the package version unambiguously.
readme = ROOT / "README.md"
if readme.exists() and version and version not in readme.read_text(encoding="utf-8"):
    err("README.md does not mention current VERSION")

# Current decision protocol/resources must be present and operational docs must not route to removed v2.
current_required = [
    "benchmark/ablation/spec-v3.json",
    "scripts/ablate_signals_v3.py",
    "scripts/run_external_heldout_gate.py",
    "scripts/prepare_ab_eval.py",
    "scripts/aggregate_ab_eval.py",
    "tests/test_ablation_v3.py",
    "tests/test_ab_eval_tools.py",
]
for rel in current_required:
    if not (ROOT / rel).exists():
        err(f"missing current protocol resource: {rel}")

operational_docs = [
    "SKILL.md",
    "README.md",
    "NETWORK_EXECUTION.md",
    "DATA_PLAN.md",
    "ROADMAP.md",
    "quality/QUALITY_MODEL.md",
    "evals/README.md",
    "benchmark/ablation/README.md",
    "benchmark/external-heldout/README.md",
    "benchmark/external-heldout/NETWORK_GATE.md",
]
stale_patterns = ["ablate_signals_v2.py", "spec-v2.json", "ABLATION_DECISION_V2.json", "external held-out v2"]
for rel in operational_docs:
    path = ROOT / rel
    if not path.exists():
        err(f"missing operational documentation: {rel}")
        continue
    text = path.read_text(encoding="utf-8")
    for stale in stale_patterns:
        if stale in text:
            err(f"stale v2 operational reference in {rel}: {stale}")

# Distilled prompt must identify the exact package version; otherwise installed variants are ambiguous.
lite = ROOT / "dist/human-writing-ru-lite.md"
if not lite.exists():
    err("dist/human-writing-ru-lite.md missing")
else:
    lite_text = lite.read_text(encoding="utf-8")
    if version and version not in lite_text:
        err("dist/human-writing-ru-lite.md does not mention current VERSION")
    if len(lite_text) > MAX_LITE_CHARACTERS:
        err(f"dist/human-writing-ru-lite.md exceeds {MAX_LITE_CHARACTERS} characters")
    if lite_text != render_lite():
        err("dist/human-writing-ru-lite.md is stale; run scripts/build_lite.py")
    try:
        validate_lite(lite_text)
    except ValueError as exc:
        err(f"invalid dist/human-writing-ru-lite.md: {exc}")

# Structural validation of the external source registry. This is deliberately lightweight and dependency-free.
registry_path = ROOT / "benchmark/external-heldout/SOURCE_REGISTRY.json"
registry = json_cache.get(registry_path)
profile_path = ROOT / "profiles/editorial-baseline.json"
profile_data = json_cache.get(profile_path)
known_profiles = set(profile_data.get("profiles", {})) if isinstance(profile_data, dict) else set()
if isinstance(registry, dict):
    if version and registry.get("generated_for_release") != version:
        err(f"SOURCE_REGISTRY generated_for_release != VERSION: {registry.get('generated_for_release')!r} != {version!r}")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        err("SOURCE_REGISTRY sources missing/empty")
    else:
        for i, source in enumerate(sources):
            prefix = f"SOURCE_REGISTRY sources[{i}]"
            if not isinstance(source, dict):
                err(prefix + " must be an object")
                continue
            for key in ("id", "adapter", "source_url", "redistribution", "status"):
                if not isinstance(source.get(key), str) or not source.get(key, "").strip():
                    err(f"{prefix}: missing/empty {key}")
            profiles = source.get("profiles")
            if not isinstance(profiles, list) or not profiles or any(not isinstance(x, str) or not x for x in profiles):
                err(f"{prefix}: profiles must be a non-empty string list")
            elif known_profiles:
                unknown_profiles = sorted(set(profiles) - known_profiles)
                if unknown_profiles:
                    err(f"{prefix}: unknown profiles {unknown_profiles}")
            channels = source.get("channels")
            if not isinstance(channels, list) or not channels or any(not isinstance(x, str) or not x for x in channels):
                err(f"{prefix}: channels must be a non-empty string list")
else:
    err("SOURCE_REGISTRY must be an object")

# SOURCE_MANIFEST.csv is a human/CI-readable projection of the registry and must
# not silently lag behind it. Compare fields that affect routing/feasibility.
source_manifest_path = ROOT / "benchmark/external-heldout/SOURCE_MANIFEST.csv"
if isinstance(registry, dict) and isinstance(registry.get("sources"), list):
    if not source_manifest_path.exists():
        err("benchmark/external-heldout/SOURCE_MANIFEST.csv missing")
    else:
        try:
            with source_manifest_path.open(encoding="utf-8", newline="") as fh:
                source_manifest_rows = list(csv.DictReader(fh))
            actual_projection = {
                (row.get("source_id") or "").strip(): (
                    (row.get("profiles") or "").strip(),
                    (row.get("channels") or "").strip(),
                    (row.get("adapter") or "").strip(),
                    (row.get("status") or "").strip(),
                )
                for row in source_manifest_rows
                if (row.get("source_id") or "").strip()
            }
            expected_projection = {
                source["id"]: (
                    ";".join(source.get("profiles", [])),
                    ";".join(source.get("channels", [])),
                    source.get("adapter", ""),
                    source.get("status", ""),
                )
                for source in registry["sources"]
                if isinstance(source, dict) and source.get("id")
            }
            if actual_projection != expected_projection:
                missing = sorted(set(expected_projection) - set(actual_projection))
                extra = sorted(set(actual_projection) - set(expected_projection))
                changed = sorted(k for k in set(actual_projection) & set(expected_projection) if actual_projection[k] != expected_projection[k])
                err(f"SOURCE_MANIFEST projection != SOURCE_REGISTRY: missing={missing} extra={extra} changed={changed}")
        except Exception as exc:
            err(f"SOURCE_MANIFEST.csv unreadable: {exc}")

# The registry itself must make every preregistered v3 diversity gate achievable in principle.
# This does not claim that sources are materialized; it only prevents an impossible benchmark design.
spec3_path = ROOT / "benchmark/ablation/spec-v3.json"
spec3 = json_cache.get(spec3_path)
if isinstance(registry, dict) and isinstance(spec3, dict):
    sources = [
        s for s in registry.get("sources", [])
        if isinstance(s, dict)
        and s.get("adapter") != "manual_reference_only"
        and "format_unverified" not in str(s.get("status", ""))
    ]
    for profile, cfg in spec3.get("diversity_gate", {}).items():
        candidates = [s for s in sources if profile in s.get("profiles", [])]
        source_ids = {s.get("id") for s in candidates if s.get("id")}
        channels = {ch for s in candidates for ch in s.get("channels", []) if isinstance(ch, str) and ch}
        if len(source_ids) < int(cfg.get("minimum_sources", 0)):
            err(f"SOURCE_REGISTRY cannot satisfy v3 minimum_sources for {profile}: {len(source_ids)}")
        if len(channels) < int(cfg.get("minimum_channels", 0)):
            err(f"SOURCE_REGISTRY cannot satisfy v3 minimum_channels for {profile}: {len(channels)}")
        if cfg.get("author_concentration_required"):
            author_capable = [s for s in candidates if s.get("author_provenance_capable") is True]
            if not author_capable:
                err(f"SOURCE_REGISTRY cannot satisfy v3 author provenance for {profile}: no eligible author_provenance_capable source")


# TZ rule/profile contracts (separate from frozen editorial policy).
tz_rules_path = ROOT / "profiles/tz-rules.ru.json"
tz_profiles_path = ROOT / "profiles/tz-profiles.json"
if not tz_rules_path.exists():
    err("profiles/tz-rules.ru.json missing")
else:
    tz_rules = read_json(tz_rules_path)
    if isinstance(tz_rules, dict):
        if tz_rules.get("language") != "ru": err("TZ rules language must be ru")
        ids=[]
        for idx, rule in enumerate(tz_rules.get("rules", [])):
            if not isinstance(rule, dict): err(f"TZ rule {idx} must be object"); continue
            rid=rule.get("id"); ids.append(rid)
            for key in ("id","category","severity","title_ru","message_ru","fix_ru"):
                if not isinstance(rule.get(key), str) or not rule.get(key): err(f"TZ rule {idx}: missing {key}")
            if rule.get("safe_autofix") is not False: err(f"TZ rule {rid}: semantic safe_autofix must be false")
        if len(ids) != len(set(ids)): err("duplicate TZ rule IDs")
if not tz_profiles_path.exists():
    err("profiles/tz-profiles.json missing")
else:
    tz_profiles = read_json(tz_profiles_path)
    if isinstance(tz_profiles, dict):
        names=set(tz_profiles.get("profiles",{}))
        if names != {"generic","gost34","gost19"}: err(f"unexpected TZ profiles: {sorted(names)}")
if not (ROOT/"scripts/check_tz_ru.py").exists(): err("scripts/check_tz_ru.py missing")
if not (ROOT/"references/technical-specification.md").exists(): err("references/technical-specification.md missing")

print(f"errors: {len(errors)} warnings: {len(warnings)}")
for message in errors:
    print("ERROR:", message)
for message in warnings:
    print("WARN:", message)
raise SystemExit(1 if errors else 0)
