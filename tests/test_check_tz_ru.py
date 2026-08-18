#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tz',ROOT/'scripts/check_tz_ru.py')
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
def codes(text,profile='generic'): return {f['code'] for f in mod.analyze(text,profile)['findings']}

def main():
    bad="# Требования\n- Система должна работать максимально быстро и удобно.\n- Система должна по возможности обеспечивать безопасность.\n- Отчёт должен формироваться в кратчайшие сроки.\n- Система должна обработать это и сохранить результат.\n- TODO: согласовать лимит пользователей.\nREQ-003: Желательно сохранять расширенный журнал.\n"
    c=codes(bad)
    for expected in {'TZ001','TZ002','TZ003','TZ005','TZ006','TZ007','TZ008','TZ009','TZ012'}:
        assert expected in c,(expected,c)
    good="# Требования\nREQ-001: API должен возвращать HTTP 200 и идентификатор созданной записи при успешном POST /items.\nREQ-002: При 100 одновременных запросах p95 времени ответа должен быть не более 800 мс в тестовой конфигурации X.\n\n# Критерии приёмки\nREQ-001 проверяется интеграционным тестом: после POST /items ответ содержит HTTP 200 и непустой id.\nREQ-002 проверяется нагрузочным тестом при 100 одновременных запросах; p95 не более 800 мс.\n"
    cg=codes(good)
    assert 'TZ002' not in cg and 'TZ005' not in cg and 'TZ012' not in cg,cg
    assert 'TZ004' not in codes('Система должна принять имя и фамилию пользователя.\n\n# Критерии приёмки\nПоле сохраняется.')
    src='Система\u00a0должна обработать 100 запросов. \n'; dst=mod.safe_normalize(src)
    assert dst=='Система должна обработать 100 запросов.\n',repr(dst)
    code='```text\nTODO: example only\n```\n# Критерии приёмки\nЕсть.\n'
    assert 'TZ001' not in codes(code)
    dup='# Критерии приёмки\n- Система должна сохранять журнал событий.\n- Система должна сохранять журнал событий.\n'
    assert 'TZ010' in codes(dup)
    g19=mod.analyze('# Введение\nТекст\n# Требования к программе\nСистема должна работать.\n# Порядок контроля и приемки\nТест.\n','gost19')
    assert any(f['code']=='TZ014' for f in g19['findings'])
    assert 'TZ014' not in codes(good,'generic')
    g34_complete='''# Общие сведения
# Цели и назначение создания автоматизированной системы
# Характеристика объектов автоматизации
# Требования к автоматизированной системе
# Состав и содержание работ по созданию автоматизированной системы
# Порядок разработки автоматизированной системы
# Порядок контроля и приемки автоматизированной системы
# Требования к составу и содержанию работ по подготовке объекта автоматизации к вводу автоматизированной системы в действие
# Требования к документированию
# Источники разработки
'''
    assert not any(f['code']=='TZ014' for f in mod.analyze(g34_complete,'gost34')['findings'])
    g19_complete='''# Введение
# Основания для разработки
# Назначение разработки
# Требования к программе или программному изделию
# Требования к программной документации
# Технико-экономические показатели
# Стадии и этапы разработки
# Порядок контроля и приемки
'''
    assert not any(f['code']=='TZ014' for f in mod.analyze(g19_complete,'gost19')['findings'])
    print('test_check_tz_ru: OK')
if __name__=='__main__': main()
