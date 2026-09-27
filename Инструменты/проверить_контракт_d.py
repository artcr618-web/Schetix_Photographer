#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет публичный контракт результата calc(): объекта d.

Контракт описан в Инструменты/контракт_d.json. Проверка намеренно не вычисляет
финансы: она защищает границу передачи данных calc.html → report.html / price.html.
Запуск: python3 Инструменты/проверить_контракт_d.py [корень]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]).resolve()
TOOLS = ROOT / 'Инструменты'
CONTRACT_PATH = TOOLS / 'контракт_d.json'
SNAPSHOT_PATH = TOOLS / 'эталоны' / 'browser_default_calc.json'
ok, fail = [], []


def check(name, condition, detail=''):
    (ok if condition else fail).append((name, detail))


def type_of(value):
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    if value is None:
        return 'null'
    return type(value).__name__


def member_reads(source, variable):
    return set(re.findall(r'(?<![\w$])' + re.escape(variable) + r'\.([A-Za-z_$][\w$]*)', source))


def shape_check(items, required, expected_types, label):
    if not isinstance(items, list):
        return f'{label} — не массив'
    for number, item in enumerate(items):
        if not isinstance(item, dict):
            return f'{label}[{number}] — не объект'
        missing = [key for key in required if key not in item]
        if missing:
            return f'{label}[{number}] — нет ' + ', '.join(missing)
        for key, expected in expected_types.items():
            actual = type_of(item[key])
            choices = expected.split('|')
            if actual not in choices:
                return f'{label}[{number}].{key}: {actual}, ожидался {expected}'
    return ''


def main():
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding='utf-8'))
    data = snapshot['result']
    fields = contract['fields']
    field_names = set(fields)

    check('контракт имеет версию и фиксированный источник',
          contract.get('format') == 1 and contract.get('source', {}).get('producer') == 'Веб/calc.html · calc()')
    check('browser-default snapshot содержит ровно контрактные поля',
          set(data) == field_names and len(data) == contract['source']['exactTopLevelFieldCount'],
          f"snapshot={len(data)}, contract={len(field_names)}, лишние={sorted(set(data)-field_names)}, отсутствуют={sorted(field_names-set(data))}")

    grouped = []
    for group, meta in contract['groups'].items():
        grouped.extend(meta['fields'])
        check(f'группа {group} имеет название и единицу', bool(meta.get('title')) and bool(meta.get('unit')))
    check('группы покрывают контракт без дублей',
          set(grouped) == field_names and len(grouped) == len(set(grouped)),
          f'в группах={len(grouped)}, уникальных={len(set(grouped))}, полей={len(field_names)}')

    wrong_types = []
    wrong_groups = []
    for key, meta in fields.items():
        actual = type_of(data[key])
        expected = meta['type']
        if actual not in expected.split('|'):
            wrong_types.append(f'{key}: {actual} ≠ {expected}')
        if meta.get('group') not in contract['groups'] or key not in contract['groups'][meta['group']]['fields']:
            wrong_groups.append(key)
    check('типы полей browser-default соответствуют контракту', not wrong_types, '; '.join(wrong_types[:5]))
    check('каждое поле указывает на собственную группу', not wrong_groups, ', '.join(wrong_groups))

    shapes = contract['shapes']
    answer_problem = shape_check(data['answers'], shapes['answers']['itemRequired'], shapes['answers']['itemTypes'], 'answers')
    catalog_problem = shape_check(data['catalog'], shapes['catalog']['itemRequired'], shapes['catalog']['itemTypes'], 'catalog')
    check('answers имеет утверждённую форму активных ответов', not answer_problem, answer_problem)
    check('catalog имеет утверждённую форму позиций', not catalog_problem, catalog_problem)
    load_problem = ''
    load_shape = shapes['loadGoal/loadCur/loadZero']
    for key in ('loadGoal', 'loadCur', 'loadZero'):
        value = data[key]
        if value is None and load_shape['nullable']:
            continue
        if not isinstance(value, dict):
            load_problem = f'{key}: {type_of(value)}'
            break
        missing = [name for name in load_shape['itemRequired'] if name not in value]
        invalid = [name for name in load_shape['itemRequired'] if name in value and type_of(value[name]) != 'number']
        if missing or invalid:
            load_problem = f'{key}: нет {missing}; не числа {invalid}'
            break
    check('loadGoal/loadCur/loadZero имеют утверждённую форму или null', not load_problem, load_problem)

    plan_problem = ''
    plan_shape = shapes['projectPlan']
    plan = data.get('projectPlan')
    if not isinstance(plan, dict):
        plan_problem = 'projectPlan — не объект'
    else:
        missing = [key for key in plan_shape['required'] if key not in plan]
        if missing:
            plan_problem = 'projectPlan — нет ' + ', '.join(missing)
        elif (type_of(plan['version']) != 'number' or type_of(plan['weeks']) != 'number'
              or type_of(plan['step']) != 'number' or type_of(plan['minShoot']) != 'number'
              or type_of(plan['capacity']) != 'number' or not isinstance(plan['projects'], list)):
            plan_problem = 'projectPlan — неверные скалярные поля или projects'
        else:
            plan_problem = shape_check(plan['projects'], plan_shape['projectRequired'],
                                       {key: 'number' for key in plan_shape['projectRequired']},
                                       'projectPlan.projects')
            for section, required in (('regular', plan_shape['regularRequired']),
                                      ('totals', plan_shape['totalsRequired'])):
                value = plan.get(section)
                bad = [key for key in required if not isinstance(value, dict) or type_of(value.get(key)) != 'number']
                if bad and not plan_problem:
                    plan_problem = 'projectPlan.' + section + ' — нет или не числа ' + ', '.join(bad)
    check('projectPlan имеет утверждённую форму ядра B008', not plan_problem, plan_problem)

    report = (ROOT / 'Веб' / 'report.html').read_text(encoding='utf-8')
    price = (ROOT / 'Веб' / 'price.html').read_text(encoding='utf-8')
    report_raw = member_reads(report, 'd') | member_reads(report, 'Д')
    price_raw = member_reads(price, 'Д')
    report_reads = report_raw & field_names
    price_reads = price_raw & field_names
    report_declared = {key for key, meta in fields.items() if 'report' in meta['consumers']}
    price_declared = {key for key, meta in fields.items() if 'price' in meta['consumers']}
    check('report читает в точности объявленные поля контракта', report_reads == report_declared,
          f'не описаны={sorted(report_reads-report_declared)}; устарели={sorted(report_declared-report_reads)}')
    check('price читает в точности объявленные поля контракта', price_reads == price_declared,
          f'не описаны={sorted(price_reads-price_declared)}; устарели={sorted(price_declared-price_reads)}')

    compat = contract['compatibility']
    allowed_report = set(compat['allowedNonDataMemberReads'])
    unknown_report = report_raw - field_names - allowed_report
    unknown_price = price_raw - field_names
    check('report не обращается к неописанному полю d', not unknown_report, ', '.join(sorted(unknown_report)))
    check('price не обращается к неописанному полю d', not unknown_price, ', '.join(sorted(unknown_price)))

    calc = (ROOT / 'Веб' / 'calc.html').read_text(encoding='utf-8')
    check('directFrameCosts передаётся calc() и не пересчитывается отчётом',
          fields.get('directFrameCosts', {}).get('group') == 'costBreakdown'
          and fields.get('directFrameCosts', {}).get('consumers') == ['report']
          and 'directFrameCosts:directFrameCosts' in calc
          and 'Number(Д.directFrameCosts)||0' in report
          and 'var прямые = (Д.directFrameCosts>0)' not in report,
          'ожидалось готовое поле calc() без fallback-формулы в report.html')
    check('канал передачи использует phc_report и ?data',
          "localStorage.setItem('phc_report'" in calc
          and "localStorage.getItem('phc_report')" in report
          and "location.search.match(/[?&]data=" in report
          and "localStorage.getItem('phc_report')" in price
          and "location.search.match(/[?&]data=" in price)

    for name, detail in ok:
        print('  ✓ ' + name + (f' — {detail}' if detail else ''))
    for name, detail in fail:
        print('  ✗ ' + name + (f' — {detail}' if detail else ''))
    print(f'\nконтракт d: {len(ok)} прошло · {len(fail)} упало')
    raise SystemExit(1 if fail else 0)


if __name__ == '__main__':
    main()
