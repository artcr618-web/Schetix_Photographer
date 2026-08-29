#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Строит перекрёстные карты связей проекта СЧЁТИКС.
Запуск:  python3 карта.py [корень_проекта]
Кладёт TSV-индексы в audit/index/ и печатает сводку."""
import re, io, os, sys, collections, openpyxl

КОРЕНЬ = sys.argv[1] if len(sys.argv) > 1 else '/home/user/schetix'
ВЫХОД  = '/home/user/audit/index'
os.makedirs(ВЫХОД, exist_ok=True)
ФАЙЛЫ  = {'calc': 'Веб/calc.html', 'report': 'Веб/report.html', 'index': 'Веб/index.html'}

def читать(п): return io.open(os.path.join(КОРЕНЬ, п), encoding='utf-8').read()
S = {k: читать(v) for k, v in ФАЙЛЫ.items()}

def css_блок(s):
    return '\n'.join(re.findall(r'<style[^>]*>([\s\S]*?)</style>', s))
def js_блок(s):
    return '\n'.join(re.findall(r'<script[^>]*>([\s\S]*?)</script>', s))
def разметка(s):
    s = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', s)
    s = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', s)
    return s

# ─────────────────────────────────────────── 1. ID
def карта_id():
    строк = []
    for имя, s in S.items():
        м, js = разметка(s), js_блок(s)
        объявлены = collections.Counter(re.findall(r'\bid="([^"]+)"', м))
        # id, создаваемые динамически в JS-строках
        динам = set(re.findall(r"id=[\\]?['\"]([\w-]+)", js))
        for i, n in sorted(объявлены.items()):
            польз = len(re.findall(r"\$\(['\"]%s['\"]\)" % re.escape(i), js)) \
                  + len(re.findall(r"getElementById\(['\"]%s['\"]\)" % re.escape(i), js))
            в_css = len(re.findall(r'#%s\b' % re.escape(i), css_блок(s)))
            строк.append((имя, i, n, польз, в_css,
                          'ДУБЛЬ' if n > 1 else ('мёртвый' if польз == 0 and в_css == 0 else 'ok')))
        for i in sorted(динам - set(объявлены)):
            строк.append((имя, i, 0, 0, len(re.findall(r'#%s\b' % re.escape(i), css_блок(s))), 'динамический'))
    with io.open(os.path.join(ВЫХОД, 'ids.tsv'), 'w', encoding='utf-8') as f:
        f.write('файл\tid\tобъявлен_раз\tобращений_JS\tв_CSS\tстатус\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

# ─────────────────────────────────────────── 2. CSS-классы
def карта_классов():
    строк = []
    for имя, s in S.items():
        css, м, js = css_блок(s), разметка(s), js_блок(s)
        # объявленные селекторы классов
        объявл = collections.Counter()
        for правило in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            сел = правило.group(1)
            if '@' in сел: continue
            for c in re.findall(r'\.([\w-]+)', сел): объявл[c] += 1
        в_разметке = set(w for a in re.findall(r'class="([^"]+)"', м) for w in a.split())
        в_js = set(w for a in re.findall(r"class=[\\]?['\"]([^'\"\\]+)", js) for w in a.split())
        в_js |= set(re.findall(r"classList\.[a-z]+\(['\"]([\w-]+)", js))
        в_js |= set(re.findall(r"querySelector(?:All)?\(['\"][^'\"]*\.([\w-]+)", js))
        для_печати = объявл.keys() | в_разметке | в_js
        for c in sorted(для_печати):
            d, r_, j = объявл.get(c, 0), c in в_разметке, c in в_js
            статус = 'ok'
            if d and not r_ and not j: статус = 'НЕиспользуется'
            elif not d and (r_ or j):  статус = 'БЕЗ_стиля'
            elif d > 6:                статус = 'много_правил(%d)' % d
            строк.append((имя, c, d, int(r_), int(j), статус))
    with io.open(os.path.join(ВЫХОД, 'classes.tsv'), 'w', encoding='utf-8') as f:
        f.write('файл\tкласс\tправил_CSS\tв_разметке\tв_JS\tстатус\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

# ─────────────────────────────────────────── 3. Палитра
def карта_палитры(книга):
    ws = книга['09c_Палитра']
    в_книге = {}
    for r in range(1, ws.max_row + 1):
        t = ws.cell(r, 1).value; hexv = ws.cell(r, 2).value; где = ws.cell(r, 4).value
        if isinstance(t, str) and t.strip().startswith('--'):
            в_книге[t.strip()] = ((hexv or '').strip() if isinstance(hexv, str) else str(hexv), (где or '').strip(), r)
    строк = []
    все = set(в_книге)
    объявл = {}
    for имя, s in S.items():
        css = css_блок(s)
        объявл[имя] = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;}]+)', css))
        все |= set(объявл[имя])
    for t in sorted(все):
        b = в_книге.get(t, ('', '', ''))
        строка = [t, b[0], b[2]]
        for имя in ФАЙЛЫ:
            v = объявл[имя].get(t, '').strip()
            польз = len(re.findall(r'var\(%s\)' % re.escape(t), S[имя]))
            строка += [v, польз]
        # расхождение hex между книгой и файлами
        цвета = {объявл[и].get(t, '').strip().lower() for и in ФАЙЛЫ if объявл[и].get(t)}
        стат = 'ok'
        if not b[0] and цвета: стат = 'нет_в_книге'
        elif b[0] and not цвета: стат = 'нет_в_коде'
        elif len(цвета) > 1: стат = 'РАЗНЫЕ_в_файлах'
        elif b[0] and цвета and b[0].lower() not in цвета: стат = 'РАСХОЖДЕНИЕ_с_книгой'
        строк.append(строка + [стат])
    with io.open(os.path.join(ВЫХОД, 'palette.tsv'), 'w', encoding='utf-8') as f:
        f.write('токен\tкнига_hex\tстрока_книги\t' + '\t'.join('%s_знач\t%s_использ' % (k, k) for k in ФАЙЛЫ) + '\tстатус\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

# ─────────────────────────────────────────── 4. Каталоги: книга vs CAT
def карта_каталога(книга):
    ws = книга['03_Каталоги']
    из_книги = []
    for r in range(5, ws.max_row + 1):
        форма = ws.cell(r, 1).value
        if not форма: continue
        из_книги.append((str(форма).strip(), str(ws.cell(r, 2).value).strip(),
                         ws.cell(r, 3).value, ws.cell(r, 4).value, ws.cell(r, 5).value, r))
    js = js_блок(S['calc'])
    i = js.find('var CAT=')
    хвост = js[i:js.index('};', i) + 2]
    из_кода = []
    for m in re.finditer(r"(Form\d+):\{k:'(\w+)',rows:\[([\s\S]*?)\]\}", хвост):
        форма, k, тело = m.group(1), m.group(2), m.group(3)
        for row in re.finditer(r"\['((?:[^'\\]|\\.)*)',([\d.]+),([\d.]+)\]", тело):
            имя = row.group(1).encode().decode('unicode_escape')
            из_кода.append((форма, имя, float(row.group(2)), float(row.group(3)), k))
    строк = []
    исп_код = [False] * len(из_кода)
    for форма, имя, цена, срок, период, r in из_книги:
        найдено = None
        for idx, (f2, n2, c2, x2, k2) in enumerate(из_кода):
            if f2 == форма and n2.replace('–', '-') == имя.replace('–', '-'):
                найдено = idx; break
        if найдено is None:
            строк.append((форма, имя, цена, срок or период, '—', '—', 'НЕТ_В_КОДЕ', r))
        else:
            исп_код[найдено] = True
            f2, n2, c2, x2, k2 = из_кода[найдено]
            ожид = срок if срок else {'Год': 1, 'Квартал': 4, 'Месяц': 12}.get(str(период), None)
            ст = 'ok'
            if float(цена) != c2: ст = 'ЦЕНА_РАЗНАЯ'
            elif ожид is not None and float(ожид) != x2: ст = 'СРОК/ПЕРИОД_РАЗНЫЙ'
            строк.append((форма, имя, цена, ожид, c2, x2, ст, r))
    for idx, (f2, n2, c2, x2, k2) in enumerate(из_кода):
        if not исп_код[idx]:
            строк.append((f2, n2, '—', '—', c2, x2, 'НЕТ_В_КНИГЕ', ''))
    with io.open(os.path.join(ВЫХОД, 'catalog.tsv'), 'w', encoding='utf-8') as f:
        f.write('форма\tпозиция\tкнига_цена\tкнига_срок\tкод_цена\tкод_срок\tстатус\tстрока_книги\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

# ─────────────────────────────────────────── 5. Параметры: книга vs дефолты формы
СВЯЗЬ = {  # ID книги -> id поля в анкете
 'income_month':'income_month','current_rate':'current_rate','frames_out':'frames_out',
 'shoot_duration':'shoot_manual','post_ratio':'post_ratio','client_time':'client_time',
 'promo_per_day':'promo_per_day','acc_per_quarter':'acc_per_quarter','acc_cost_month':'acc_cost_month',
 'home_rent':'home_rent','home_util':'home_util','home_area':'home_area','cab_area':'cab_area',
 'office_rent':'office_rent','office_util':'office_util','edu_life':'edu_life',
 'site_cost':'site_cost','site_hours':'site_hours','site_life':'site_life',
 'acq_rate':'acq_rate','acq_share':'acq_share','fm_pct':'fm_pct',
}
def карта_параметров(книга):
    ws = книга['calc']
    зн = {}
    for r in range(1, ws.max_row + 1):
        i = ws.cell(r, 1).value
        if isinstance(i, str) and i.strip() in СВЯЗЬ:
            зн[i.strip()] = (ws.cell(r, 3).value, r)
    поля = dict((m.group(1), m.group(2)) for m in
                re.finditer(r'<input[^>]*id="([\w]+)"[^>]*value="([^"]*)"', S['calc']))
    поля.update(dict((m.group(2), m.group(1)) for m in
                re.finditer(r'<input[^>]*value="([^"]*)"[^>]*id="([\w]+)"', S['calc'])))
    строк = []
    for пид, (v, r) in sorted(зн.items()):
        поле = СВЯЗЬ[пид]; hv = поля.get(поле, '')
        try:
            bv = float(v); hf = float(str(hv).replace(' ', '').replace(',', '.'))
            if пид in ('fm_pct',) and bv < 1: bv *= 100
            if пид in ('acq_rate',) and bv < 1: bv *= 100
            if пид in ('acq_share',) and bv <= 1: bv *= 100
            ст = 'ok' if abs(bv - hf) < 1e-9 else 'РАСХОЖДЕНИЕ'
        except Exception:
            bv, hf, ст = v, hv, '?'
        строк.append((пид, поле, bv, hf, ст, r))
    with io.open(os.path.join(ВЫХОД, 'params.tsv'), 'w', encoding='utf-8') as f:
        f.write('ID_книги\tполе_формы\tкнига\tформа\tстатус\tстрока_книги\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

# ─────────────────────────────────────────── 6. Поток данных d: анкета → отчёт
def карта_потока():
    js = js_блок(S['calc'])
    # контракт return{} менял порядок полей (раньше первым был frames:,
    # теперь answers:) — ищем сам объект целиком, а не конкретное поле
    i = js.find('return{frames:')
    if i < 0: i = js.find('return{')
    хвост = js[i:js.index('};', i)]
    поля = re.findall(r'([A-Za-zА-Яа-я_]\w*)\s*:', хвост)
    поля = list(dict.fromkeys(поля))
    rjs = js_блок(S['report'])
    строк = []
    for p in поля:
        n = len(re.findall(r'\b(?:d|x)\.%s\b' % re.escape(p), rjs))
        demo = bool(re.search(r'\b%s\s*:' % re.escape(p), rjs[rjs.find('DEMO='):rjs.find('DEMO=') + 1200]))
        строк.append((p, n, 'да' if demo else 'НЕТ', 'ok' if n else 'НЕ_ЧИТАЕТСЯ'))
    with io.open(os.path.join(ВЫХОД, 'dataflow.tsv'), 'w', encoding='utf-8') as f:
        f.write('поле\tобращений_в_отчёте\tесть_в_DEMO\tстатус\n')
        for r in строк: f.write('\t'.join(map(str, r)) + '\n')
    return строк

if __name__ == '__main__':
    книга = openpyxl.load_workbook(os.path.join(КОРЕНЬ, 'Книга', 'Калькулятор_ставки_часа.xlsx'))
    ids = карта_id(); cls = карта_классов(); pal = карта_палитры(книга)
    cat = карта_каталога(книга); par = карта_параметров(книга); flow = карта_потока()
    print('ids.tsv      %5d строк | дублей %d, мёртвых %d' % (
        len(ids), sum(1 for r in ids if r[5] == 'ДУБЛЬ'), sum(1 for r in ids if r[5] == 'мёртвый')))
    print('classes.tsv  %5d | без стиля %d, неиспользуемых %d' % (
        len(cls), sum(1 for r in cls if r[5] == 'БЕЗ_стиля'), sum(1 for r in cls if r[5] == 'НЕиспользуется')))
    print('palette.tsv  %5d | проблем %d' % (len(pal), sum(1 for r in pal if r[-1] != 'ok')))
    print('catalog.tsv  %5d | проблем %d' % (len(cat), sum(1 for r in cat if r[6] != 'ok')))
    print('params.tsv   %5d | расхождений %d' % (len(par), sum(1 for r in par if r[4] != 'ok')))
    print('dataflow.tsv %5d | не читается отчётом %d' % (len(flow), sum(1 for r in flow if r[3] != 'ok')))
