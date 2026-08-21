# -*- coding: utf-8 -*-
"""Пересобирает демо-набор в report.html и части/каркас.html.
Демо — это расчёт по значениям анкеты по умолчанию, а не выдуманные числа.
Запуск: python3 части/демо.py"""
import os as _os
# Корень проекта ищем вверх от файла — по книге. Переезд папок ничего не ломает.
def _найти_корень(старт):
    п = _os.path.dirname(_os.path.abspath(старт))
    while п != '/':
        if _os.path.exists(_os.path.join(п, 'Калькулятор_ставки_часа.xlsx')): return п
        п = _os.path.dirname(п)
    return '/home/user/schetix'
_КОРЕНЬ = _найти_корень(__file__)
_ИНСТРУМЕНТЫ = next((п for п in (
    _os.path.join(_os.path.dirname(_КОРЕНЬ), 'ДОКУМЕНТАЦИЯ', '4_инструменты'),
    _os.path.join(_КОРЕНЬ, 'ДОКУМЕНТАЦИЯ', '4_инструменты'),
) if _os.path.isdir(п)), '')
import json, subprocess, re, io

d = json.loads(subprocess.check_output(
    ['node','харнесс.js','/home/user/schetix','{}'],
    cwd=_ИНСТРУМЕНТЫ).decode())
d.pop('__parts', None)
d['regime'] = 'Самозанятый (НПД) — 5%, смешанные заказчики'
d['regimeCode'] = 'npd5'
d['profession'] = 'фотографа'
# харнесс работает без DOM: список режимов и заказчиков ему недоступен,
# поэтому в демо-наборе подставляем те же значения, что видит человек
for _о in d.get('answers', []):
    if _о['n'] == 'Налоговый режим': _о['v'] = d['regime']
    if _о['n'] == 'С кем вы чаще работаете': _о['v'] = 'И с частными лицами, и с компаниями'

def esc(v):
    if isinstance(v, str):
        return "'" + ''.join('\\u%04x' % ord(c) if ord(c) > 127 else c for c in v) + "'"
    if isinstance(v, float):
        return repr(round(v, 5))
    return json.dumps(v, ensure_ascii=False)

пары = [f'{k}:{esc(v)}' for k, v in d.items()]
строки, тек = [], ''
for п in пары:
    if len(тек) + len(п) > 140:
        строки.append(тек); тек = ''
    тек += п + ','
строки.append(тек.rstrip(','))
литерал = ('/* ДЕМО-НАБОР. Не выдумка: это расчёт по значениям анкеты по умолчанию,\n'
           '   пересобирается скриптом части/демо.py. Показывается только по ?demo=1 —\n'
           '   без расчёта отчёт предлагает заполнить анкету, а не подсовывает чужие числа. */\n'
           'var DEMO={' + '\n'.join(строки) + '};')

for файл in ('/home/user/schetix/web/report.html', '/home/user/schetix/web/части/каркас.html'):
    s = io.open(файл, encoding='utf-8').read()
    m = re.search(r"(/\* ДЕМО[^*]*\*/\n)?var DEMO=\{.*?\};", s, re.S)
    s = s.replace(m.group(0), литерал)
    io.open(файл, 'w', encoding='utf-8').write(s)
    print('демо обновлено:', файл)
