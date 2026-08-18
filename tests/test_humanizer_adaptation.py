from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def test_humanizer_adaptation():
    ref=(ROOT/'references/ai-writing-patterns.md').read_text(encoding='utf-8')
    skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
    assert 'blader/humanizer' in ref
    assert 'Запрет длинного тире' in ref
    assert 'типографских кавычек' in ref
    assert 'ai-writing-patterns.md' in skill
    cases=json.loads((ROOT/'evals/humanizer_adaptation_cases.json').read_text(encoding='utf-8'))
    assert len(cases['cases']) >= 10
    assert any(c['id']=='HUM008' and c['expect'].startswith('do_not_flag') for c in cases['cases'])
    assert (ROOT/'THIRD_PARTY_NOTICES.md').exists()
