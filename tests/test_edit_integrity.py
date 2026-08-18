#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("integrity", ROOT / "scripts/check_edit_integrity.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def codes(src: str, dst: str) -> set[str]:
    return {x["code"] for x in mod.analyze(src, dst)["findings"]}


def main() -> None:
    assert "numeric-change" in codes("Конверсия выросла до 18%.", "Конверсия выросла до 28%.")
    assert "modality-strengthened" in codes("Это может привести к задержке.", "Это точно приведёт к задержке.")
    assert "modality-marker-loss" in codes("Это может вызвать ошибку.", "Это вызывает ошибку.")
    assert "negation-loss" in codes("Система не удаляет файлы.", "Система удаляет файлы.")
    assert "condition-loss" in codes("Если токен истёк, запрос повторяют.", "Запрос повторяют.")
    assert "attribution-loss" in codes("По данным компании, выручка выросла на 5%.", "Выручка выросла на 5%.")
    assert "url-change" in codes("См. https://example.org/a", "См. https://example.org/b")
    assert "url-change" in codes("См. https://example.org/A", "См. https://example.org/a")
    assert "url-change" not in codes("См. HTTPS://EXAMPLE.ORG/a", "См. https://example.org/a")
    assert "measurement-change" in codes("Длина кабеля 10 км.", "Длина кабеля 10 м.")
    assert "entity-like-change" in codes("Доклад подготовил Иван Петров для РАН.", "Доклад подготовил Иван Сидоров для РАН.")
    assert "entity-like-change" in codes("Система использует API и TLS.", "Система использует API.")
    assert not codes("Сервис может обработать 10 файлов.", "Сервис может обработать 10 файлов быстро.")
    assert not codes("Иван Петров использует API.", "Иван Петров использует API ежедневно.")
    print("test_edit_integrity: OK")

if __name__ == "__main__":
    main()
