# -*- coding: utf-8 -*-
"""Пересобирает технический DEMO development-отчёта из чистого calc.html.

DEMO не является отдельным расчётным сценарием: это точный снимок первого
запуска анкеты в пустом браузере. Каркас и публикационная копия здесь
намеренно не затрагиваются.

Запуск: python3 Инструменты/демо.py
Требуется: npm --prefix Инструменты ci --ignore-scripts
"""
import os as _os
# Корень проекта ищем вверх от файла — по книге. Переезд папок ничего не ломает.
def _найти_корень(старт):
    п = _os.path.dirname(_os.path.abspath(старт))
    while п != '/':
        if (_os.path.exists(_os.path.join(п, 'Калькулятор_ставки_часа.xlsx'))
            or _os.path.exists(_os.path.join(п, 'Книга', 'Калькулятор_ставки_часа.xlsx'))):
            return п
        п = _os.path.dirname(п)
    return '/home/user/schetix'

_КОРЕНЬ = _найти_корень(__file__)
import json, subprocess, re, io

_БРАУЗЕРНЫЙ_ТЕСТ = _os.path.join(_КОРЕНЬ, 'Инструменты', 'проверить_calc_browser_default.js')
d = json.loads(subprocess.check_output(
    ['node', _БРАУЗЕРНЫЙ_ТЕСТ, _КОРЕНЬ, '--assert', '--result'], text=True))


def esc(v):
    """Литерал JavaScript без потери точности чисел браузерного снимка."""
    if isinstance(v, str):
        return "'" + ''.join('\\u%04x' % ord(c) if ord(c) > 127 else c for c in v) + "'"
    if isinstance(v, float):
        return repr(v)
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def literal(data, comment):
    pairs = [f'{k}:{esc(v)}' for k, v in data.items()]
    lines, line = [], ''
    for pair in pairs:
        if len(line) + len(pair) > 140:
            lines.append(line)
            line = ''
        line += pair + ','
    lines.append(line.rstrip(','))
    return comment + '\nvar DEMO={' + '\n'.join(lines) + '};'


def replace_demo(filename, pattern, text):
    source = io.open(filename, encoding='utf-8').read()
    match = re.search(pattern, source, re.S)
    if not match:
        raise RuntimeError(f'Не найден DEMO в {filename}')
    source = source[:match.start()] + text + source[match.end():]
    io.open(filename, 'w', encoding='utf-8').write(source)
    print('демо обновлено:', _os.path.relpath(filename, _КОРЕНЬ))

report_literal = literal(d, '''/* ТЕХНИЧЕСКИЙ DEMO development-отчёта. Не отдельный пример:
   это снимок чистого старта calc.html в пустом браузере. Пересобирается
   Инструменты/демо.py; публикационная копия без DEMO — отдельная задача. */''')
replace_demo(
    _os.path.join(_КОРЕНЬ, 'Веб', 'report.html'),
    r'(?:/\*[^*]*DEMO[\s\S]*?\*/\s*)?var DEMO\s*=\s*\{.*?\};',
    report_literal)

# Прайс читает лишь эти поля, но при прямом открытии тоже обязан показывать
# ту же стартовую модель, а не исторический НПД-набор.
price_keys = ('K', 'NT', 'R', 'S', 'cl', 'discP', 'pool', 'rateWorkFull', 'sh')
price_literal = 'var DEMO = ' + json.dumps({key: d[key] for key in price_keys}, ensure_ascii=False,
                                            separators=(',', ':')) + ';'
replace_demo(
    _os.path.join(_КОРЕНЬ, 'Веб', 'price.html'),
    r'var DEMO\s*=\s*\{.*?\};',
    price_literal)
