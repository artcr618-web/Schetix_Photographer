#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает все фактические значения по умолчанию из Веб/calc.html.

Источник — рабочая HTML-анкета, а не старые листы Excel. В TSV попадают:
обычные поля, checkbox, radio, select и каждая строка динамических каталогов CAT.

Запуск:
    python3 Инструменты/значения_по_умолчанию.py [выход.tsv]
"""
from pathlib import Path
from bs4 import BeautifulSoup
import json
import re
import subprocess
import sys


def найти_корень():
    for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        if (p / 'Веб' / 'calc.html').exists():
            return p
    raise SystemExit('Не найден корень проекта')


def чисто(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def число_или_пусто(value):
    """Числовое зеркало для формул Excel; текстовое представление не меняем."""
    s = чисто(value).replace('\u00a0', '').replace(' ', '').replace(',', '.')
    if not s or s in ('да', 'нет', 'неучаствует'):
        return ''
    try:
        return float(s)
    except ValueError:
        return ''


def js_объект(text, начало):
    """Возвращает объявление JS-объекта целиком по балансу фигурных скобок."""
    p = text.index(начало)
    b = text.index('{', p)
    level = 0
    quote = None
    esc = False
    for i in range(b, len(text)):
        ch = text[i]
        if quote:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                quote = None
            continue
        if ch in "'\"`":
            quote = ch
        elif ch == '{':
            level += 1
        elif ch == '}':
            level -= 1
            if level == 0:
                return text[b:i + 1]
    raise ValueError('Не закрыт объект ' + начало)


def каталоги(text):
    obj = js_объект(text, 'var CAT=')
    script = f"const CAT={obj}; console.log(JSON.stringify(CAT));"
    return json.loads(subprocess.check_output(['node', '-e', script], text=True))


def карта_ответов(text):
    # Человекочитаемые имена из фактического answers[] функции calc().
    result = {}
    pat = re.compile(r"отв\(\s*\d+\s*,\s*'([^']+)'\s*,\s*V\('([^']+)'\)\s*,\s*'([^']*)'\s*\)")
    for name, dom_id, unit in pat.findall(text):
        result[dom_id] = (name, unit)
    return result


def подпись(el, card, answers):
    i = el.get('id', '')
    if i in answers:
        return answers[i][0]
    label = el.find_parent('label')
    if label:
        return чисто(label.get_text(' ', strip=True))
    # Ищем ближайший вопрос/подпись перед контейнером поля.
    parent = el
    for _ in range(4):
        parent = parent.parent if parent else None
        if not parent or parent == card:
            break
        for cls in ['qlab', 'lab', 'qtitle', 'subh', 'qh', 'q']:
            found = parent.find(class_=cls)
            if found:
                return чисто(found.get_text(' ', strip=True))
    title = card.find(['h2', 'h3']) if card else None
    return чисто(title.get_text(' ', strip=True)) if title else (i or el.get('name', '') or el.name)


def единица(el, answers):
    if el.get('type') in ('checkbox', 'radio') or el.name == 'select':
        return ''
    i = el.get('id', '')
    if i in answers and answers[i][1]:
        return answers[i][1]
    p = el.parent
    for _ in range(3):
        if not p:
            break
        u = p.find(class_='un')
        if u:
            return чисто(u.get_text(' ', strip=True))
        p = p.parent
    return ''


def условие(el):
    ветки = {
        'npdWho': 'режим НПД', 'ws_home': 'рабочее место: дома',
        'ws_off': 'рабочее место: отдельное помещение',
        'site_c_w': 'сайт заказан у специалистов', 'site_h_w': 'сайт создан самостоятельно',
        'acc_h_w': 'учёт ведётся самостоятельно', 'acc_c_w': 'учёт ведёт специалист',
        'bank_acq_group': 'строка эквайринга включена',
        'bank_share_row': 'строка эквайринга включена',
        'disc_lvls': 'Резерв на программу лояльности включён',
    }
    for p in [el, *el.parents]:
        if getattr(p, 'get', None) and p.get('id') in ветки:
            return ветки[p.get('id')]
    return ''


def основное_значение(el):
    typ = el.get('type', el.name)
    if typ in ('checkbox', 'radio'):
        return 'да' if el.has_attr('checked') else 'нет'
    if el.name == 'select':
        opt = el.find('option', selected=True) or el.find('option')
        return opt.get('value', '') if opt else ''
    return el.get('value', '')


def варианты(el):
    if el.name == 'select':
        return ' | '.join(f"{o.get('value','')} — {чисто(o.get_text(' ', strip=True))}"
                          for o in el.find_all('option'))
    if el.get('type') == 'radio':
        return el.get('value', '')
    return ''


root = найти_корень()
html = (root / 'Веб' / 'calc.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')
answers = карта_ответов(html)
cat = каталоги(html)

# Состояния переключателей нужны, чтобы различать сырые и эффективные дефолты.
radio_selected = {}
for r in soup.select('input[type="radio"][name]'):
    if r.has_attr('checked') or r.get('name') not in radio_selected:
        radio_selected[r.get('name')] = r.get('value','')
select_selected = {}
for s in soup.select('select[id]'):
    o = s.find('option', selected=True) or s.find('option')
    select_selected[s.get('id')] = o.get('value','') if o else ''
checked = {x.get('id'): x.has_attr('checked') for x in soup.select('input[type="checkbox"][id]')}
branch_rule = {
    'CALC-B008-S01': ('regime', 'npd'),
    'CALC-B018-S01': ('ws_mode', 'home'), 'CALC-B018-S02': ('ws_mode', 'office'),
    'CALC-B020-S01': ('site_mode', 'hired'), 'CALC-B020-S02': ('site_mode', 'self'),
    'CALC-B023-S01': ('acc_mode', 'self'), 'CALC-B023-S02': ('acc_mode', 'hired'),
    'CALC-B022-S01': ('BANK_ACQ_ON', 'true'), 'CALC-B022-S02': ('BANK_ACQ_ON', 'true'),
    'CALC-B026-S01': ('disc_on', 'true'),
}
controlled = {
    'fm_pct':'fm_on', 'fund_pct':'fund_on', 'disc_pct':'disc_on',
    'disc_lvl_5':'disc_on', 'disc_lvl_10':'disc_on', 'disc_lvl_15':'disc_on',
}
# Обратная галочка: при включении управляющего элемента поле получает
# эффективный ноль и блокируется, хотя сырое значение сохраняется.
inverse_controlled = {'home_rent':'own_home'}

def state(el, raw):
    group = branch = controller = ''
    active = True
    bp = el.find_parent(attrs={'data-branch-id': True}) if getattr(el, 'find_parent', None) else None
    if bp:
        branch = bp.get('data-branch-id','')
        group, expected = branch_rule.get(branch, ('',''))
        controller = group
        if group == 'BANK_ACQ_ON':
            active = True
        elif group in radio_selected:
            active = radio_selected[group] == expected
        elif group in select_selected:
            active = select_selected[group] == expected
        elif group in checked:
            active = checked[group] == (expected == 'true')
    eid = el.get('id','') if getattr(el, 'get', None) else ''
    if eid in controlled:
        controller = controlled[eid]; group = controller
        active = bool(checked.get(controller, False))
    if eid in inverse_controlled:
        controller = inverse_controlled[eid]; group = controller
        branch = 'выключено, когда галочка включена'
        active = not bool(checked.get(controller, False))
    if getattr(el, 'get', None) and el.get('type') == 'radio':
        group = el.get('name',''); branch = el.get('value',''); controller = group
        active = el.has_attr('checked')
    effective = raw if active else ('0' if чисто(raw) not in ('','нет','да') else 'не участвует')
    return group, branch, 'да' if active else 'нет', effective, controller

columns = [
    '№', 'Страница', '№ блока', 'Блок ID', 'Название блока', 'Тип элемента',
    'DOM / параметр ID', 'Наименование поля или позиции', 'Сырое значение по умолчанию',
    'Единица', 'Срок / период', 'Тип расчёта', 'Варианты', 'min', 'max', 'step',
    'Условие / ветка', 'Группа состояния', 'Ветка / значение',
    'Активно по умолчанию', 'Эффективное значение по умолчанию',
    'Управляющий элемент', 'Форма / каталог', 'Источник',
    'Расчётное значение за год по умолчанию',
    'Эффективное числовое значение по умолчанию',
    'Срок / период числом', 'Срок min', 'Срок max', 'Срок step'
]
rows = []
forms_by_table = {}
for table in soup.select('[id^="t_"]'):
    forms_by_table[table.get('id')[2:]] = table

for card in soup.select('#frm .card'):
    bn = card.select_one('.bn')
    block_no = чисто(bn.get_text(' ', strip=True)) if bn else ''
    title = card.find(['h2', 'h3'])
    block_title = чисто(title.get_text(' ', strip=True)) if title else ''
    block_id = card.get('id', '') or (f'CALC-B{block_no}' if block_no else '')
    for el in card.find_all(['input', 'select', 'textarea']):
        # Поля динамических таблиц описываются по CAT, не по пустому HTML-каркасу.
        if el.find_parent('table', id=re.compile(r'^t_')):
            continue
        typ = el.get('type', el.name)
        ident = el.get('id', '')
        if typ == 'radio':
            ident = f"{el.get('name','')}:{el.get('value','')}"
        elif not ident:
            ident = ('EXC:' + el.get('data-exc')) if el.get('data-exc') else el.get('name', '')
        raw = основное_значение(el)
        group, branch, active, effective, controller = state(el, raw)
        rows.append([
            '', 'Веб/calc.html', block_no, block_id, block_title, typ, ident,
            подпись(el, card, answers), raw, единица(el, answers),
            '', '', варианты(el), el.get('min', ''), el.get('max', ''), el.get('step', ''),
            условие(el), group, branch, active, effective, controller,
            '', 'HTML: value / checked / selected', '', число_или_пусто(effective), '', '', '', ''
        ])

# Привязка Form → карточка по таблице t_FormXXX.
for form, data in cat.items():
    table = forms_by_table.get(form)
    card = table.find_parent(class_='card') if table else None
    bn = card.select_one('.bn') if card else None
    block_no = чисто(bn.get_text(' ', strip=True)) if bn else ''
    title = card.find(['h2', 'h3']) if card else None
    block_title = чисто(title.get_text(' ', strip=True)) if title else ''
    block_id = card.get('id', '') if card else ''
    if not block_id and block_no:
        block_id = f'CALC-B{block_no}'
    kind = data.get('k', '')
    for n, item in enumerate(data.get('rows', []), 1):
        name = item[0] if len(item) > 0 else ''
        value = item[1] if len(item) > 1 else ''
        term = item[2] if len(item) > 2 else ''
        unit = '₽'
        term_label = f'{term} лет' if kind == 'life' else (
            f'{term} платежей/год' if kind == 'per' else f'{term} мес')
        group, branch, active, effective, controller = state(table, value) if table else ('','','да',value,'')
        # Дословное зеркало sumF() из calc.html для исходного состояния анкеты:
        # months не входит в каталоговые суммы; life делит стоимость на срок;
        # per умножает платёж на число платежей в год.
        cost = float(value or 0) if active == 'да' else 0.0
        factor = float(term or 0)
        annual = 0.0
        if kind == 'life':
            annual = cost / factor if factor > 0 else 0.0
        elif kind == 'per':
            annual = cost * factor
        if form in ('Form001', 'Form002'):
            cost_min, cost_max, cost_step = '0', '10000000', '100'
        elif form in ('Form003', 'Form004'):
            cost_min, cost_max, cost_step = '0', '100000', '100'
        elif form == 'Form013':
            cost_min, cost_max, cost_step = '0', '500000', '100'
        else:
            cost_min, cost_max, cost_step = '', '', ''
        if form in ('Form001', 'Form002', 'Form013') and kind == 'life':
            term_min, term_max, term_step = '1', '30', '1'
        elif form == 'Form004' and kind == 'life':
            term_min, term_max, term_step = '1', '10', '1'
        else:
            term_min, term_max, term_step = '', '', ''
        rows.append([
            '', 'Веб/calc.html', block_no, block_id, block_title, 'catalog_item',
            f'{form}[{n}]', name, value, unit, term_label, kind, '', cost_min, cost_max, cost_step,
            условие(table) if table else '', group, branch, active, effective, controller,
            form, 'JavaScript CAT в calc.html', annual, cost, factor,
            term_min, term_max, term_step
        ])

# Стабильная нумерация: сначала блок, затем обычные поля, затем каталог.
for i, row in enumerate(rows, 1):
    row[0] = str(i)

out = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else root / 'Документация' / 'Значения_по_умолчанию.tsv'
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', encoding='utf-8', newline='') as f:
    f.write('\t'.join(columns) + '\n')
    for row in rows:
        f.write('\t'.join(чисто(x).replace('\t', ' ') for x in row) + '\n')
print(f'{out}: {len(rows)} строк')
