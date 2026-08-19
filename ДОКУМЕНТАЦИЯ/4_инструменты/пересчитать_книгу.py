#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПЕРЕСЧЁТ КНИГИ БЕЗ EXCEL.

Проблема: в xlsx рядом с формулой хранится её последний посчитанный
результат. Если книгу собрал скрипт, результатов нет — формулы есть,
значений нет, и проверка «книга пересчитана» падает. Открыть книгу в
Excel и сохранить может только человек.

Решение: считаем формулы библиотекой formulas и вписываем результаты
прямо в xml листов, не трогая всё остальное. Диаграммы, оформление и
сами формулы остаются на месте — файл пересобирается как zip-архив.

Запуск:  python3 пересчитать_книгу.py [путь к книге]
"""
import sys, os, re, shutil, zipfile, html
import numpy as np
import formulas, openpyxl

КНИГА = sys.argv[1] if len(sys.argv) > 1 else '/home/user/schetix/Калькулятор_ставки_часа.xlsx'
ИМЯ = os.path.basename(КНИГА)

def скаляр(v):
    # formulas отдаёт значения матрицами 1×1; разворачиваем до числа.
    # Осторожно: у numpy-скаляра тоже есть .shape, но ndim == 0 —
    # без этой проверки цикл срывался в исключение и значение терялось.
    try:
        a = v.value
        while hasattr(a, 'ndim') and a.ndim > 0:
            if getattr(a, 'size', 0) != 1:
                return None
            a = a[0, 0] if a.ndim == 2 else a[0]
        return a.item() if hasattr(a, 'item') else a
    except Exception:
        return None

print('считаю формулы…')
xl = formulas.ExcelModel().loads(КНИГА).finish()
решение = {k: скаляр(v) for k, v in xl.calculate().items()}
print('посчитано ячеек:', len(решение))

wb = openpyxl.load_workbook(КНИГА)
# лист → его xml внутри архива
with zipfile.ZipFile(КНИГА) as z:
    имена = z.namelist()
    части = {n: z.read(n) for n in имена}
книга_xml = части['xl/workbook.xml'].decode()
rels = части['xl/_rels/workbook.xml.rels'].decode()
путь_листа = {}
for m in re.finditer(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="(rId\d+)"', книга_xml):
    # порядок атрибутов в rels бывает любым, поэтому ищем в обе стороны
    ц = (re.search(r'Id="%s"[^>]*?Target="([^"]+)"' % m.group(2), rels)
         or re.search(r'Target="([^"]+)"[^>]*?Id="%s"' % m.group(2), rels))
    цель = ц.group(1)
    цель = цель.lstrip('/')
    путь_листа[html.unescape(m.group(1))] = цель if цель.startswith('xl/') else 'xl/' + цель

вписано = пропущено = 0
for ws in wb.worksheets:
    формулы = [(c.coordinate, c.value) for row in ws.iter_rows() for c in row
               if isinstance(c.value, str) and c.value.startswith('=')]
    if not формулы:
        continue
    путь = путь_листа[ws.title]
    s = части[путь].decode()
    for коорд, _ in формулы:
        ключ = f"'[{ИМЯ}]{ws.title.upper()}'!{коорд}"
        зн = решение.get(ключ)
        if зн is None:
            пропущено += 1
            continue
        m = re.search(r'<c r="%s"(?P<атр>[^>]*)>(?P<тело>.*?)</c>' % коорд, s, re.S)
        if not m:
            пропущено += 1
            continue
        тело = re.sub(r'<v>.*?</v>|<v/>', '', m.group('тело'), flags=re.S)
        атр = re.sub(r'\s*t="[^"]*"', '', m.group('атр'))
        if isinstance(зн, (bool, np.bool_)):
            тип, текст = ' t="b"', '1' if зн else '0'
        elif isinstance(зн, (int, float, np.integer, np.floating)):
            тип, текст = '', repr(float(зн))
        else:
            текст = str(зн)
            тип = ' t="e"' if текст.startswith('#') else ' t="str"'
            текст = html.escape(текст)
        новая = f'<c r="{коорд}"{атр}{тип}>{тело}<v>{текст}</v></c>'
        s = s[:m.start()] + новая + s[m.end():]
        вписано += 1
    части[путь] = s.encode()

резерв = КНИГА + '.до_пересчёта'
if not os.path.exists(резерв):
    shutil.copy(КНИГА, резерв)
времен = КНИГА + '.tmp'
with zipfile.ZipFile(времен, 'w', zipfile.ZIP_DEFLATED) as z:
    for n in имена:
        z.writestr(n, части[n])
shutil.move(времен, КНИГА)
print(f'вписано значений: {вписано}, пропущено: {пропущено}')
print('резервная копия:', резерв)
