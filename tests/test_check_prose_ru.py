#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,sys,tempfile,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CHECK=ROOT/'scripts/check_prose_ru.py'
def run(text,mode='prose',include_quotes=False,features=False):
    with tempfile.NamedTemporaryFile('w',suffix='.md',encoding='utf-8',delete=False) as f: f.write(text); pth=f.name
    cmd=[sys.executable,str(CHECK),'--json','--mode',mode]
    if include_quotes: cmd.append('--include-quotes')
    if features: cmd.append('--features-only')
    cmd.append(pth); p=subprocess.run(cmd,text=True,capture_output=True); Path(pth).unlink(missing_ok=True); assert p.returncode==0,p.stderr; return json.loads(p.stdout)
def codes(r): return {x['code'] for x in r.get('findings',[])}
r=run('Нужно проверить настройку.\n\nИнженер открыл журнал.\n\nНоутбук остался на столе.',mode='oral'); assert 'filler-density' not in codes(r)
r=run('Диапазон 10–15 минут. Соотношение 1:2. Встреча в 12:30.'); assert r['features']['dash_per_1000']==0 and r['features']['colon_per_1000']==0
r=run('И. И. Иванов приехал. Версия 2.1.4 вышла позже. А. П. Петров проверил результат.'); assert r['features']['sentences']==3,r
q='Автор написал: «Это не просто функция — это переосмысление взаимодействия». Снаружи текст нейтрален.'
r=run(q); r2=run(q,include_quotes=True); assert r2['features']['words']>r['features']['words']
r=run('Было принято решение об изменении схемы. Было принято решение о повторной проверке.',mode='technical'); levels=[x['level'] for x in r['findings'] if x['code']=='nominalization']; assert levels and all(x=='info' for x in levels)
f=run('Коротко. Потом идёт заметно более длинное предложение, которое нужно только измерить, а не автоматически объявить плохим.',features=True); assert 'sentence_mean_words' in f['features'] and 'dash_per_1000' in f['features']
print('OK')
# Сокращения не должны склеивать/дробить предложения механически.
r=run('Это пример, т. е. продолжение той же фразы. И т. д. Потом новая фраза. г. Москва указан в форме. В 2020 г. Потом правило изменили.')
assert r['features']['sentences']==6, r

# Нормативные negative controls не должны автоматически становиться стилевой ошибкой.
r=run('Он выбрал не поезд, а автобус, потому что рейс отменили. Москва — столица России. Причина проста: сервер не ответил вовремя.')
assert 'rhetorical-pivot' not in codes(r), r


# Pilot policy: punctuation density stays measurable but is not a user alert by default.
dash_text = ' '.join(['Система — это набор компонентов, которые работают вместе и передают данные между этапами.' for _ in range(25)])
r=run(dash_text,mode='prose')
assert r['features']['dash_per_1000'] > 0
assert 'dash-density' not in codes(r), r

colon_text = ' '.join(['Причина проста: сервер завершил обработку запроса и вернул результат клиенту.' for _ in range(25)])
r=run(colon_text,mode='technical')
assert r['features']['colon_per_1000'] > 0
assert 'colon-density' not in codes(r), r

# A technical term may repeat without becoming a promotion warning.
seamless = ' '.join(['Бесшовный единый вход позволяет пользователю войти в систему без повторного ввода пароля.' for _ in range(8)])
r=run(seamless,mode='technical')
assert r['features']['hype_per_1000'] > 0
assert 'hype-density' not in codes(r), r

# One legitimate occurrence in general prose is not enough for a lexical warning.
r=run('Флагманский проект организации завершил первый этап испытаний и перешёл к следующей фазе.')
assert r['features']['hype_per_1000'] > 0
assert 'hype-density' not in codes(r), r

# Repeated promotional formulae must remain detectable in product/general prose.
problem = ' '.join([
    'Это новый уровень сервиса и бесшовный опыт для пользователя.',
    'Решение выводит продукт на новый уровень и создаёт уникальную экосистему.',
    'Бесшовный сценарий становится драйвером роста и новой реальностью.'
])
r=run(problem,mode='product')
assert 'hype-density' in codes(r), r
