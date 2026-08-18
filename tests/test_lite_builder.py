#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_lite.py"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("build_lite", SCRIPT)
assert SPEC and SPEC.loader
build_lite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_lite)


def main() -> None:
    text = build_lite.render_lite()
    build_lite.validate_lite(text)

    saved = (ROOT / "dist/human-writing-ru-lite.md").read_text(encoding="utf-8")
    assert saved == text, "краткая инструкция не совпадает с результатом генерации"
    assert len(text) <= 2000 < 2048

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert not re.search(r"[A-Za-z]", text.replace(version, ""))
    assert "Работай только с текстом и сведениями диалога" in text
    assert "Не обещай проверок недоступными средствами" in text
    assert "Не выдумывай опыт" in text
    assert "авторский голос" in text
    assert "scripts/" not in text and ".py" not in text and "```" not in text
    print(f"test_lite_builder: OK ({len(text)}/2000 знаков)")


if __name__ == "__main__":
    main()
