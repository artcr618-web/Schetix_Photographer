#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добавляет лист в книгу Excel, НЕ переписывая её целиком.

Зачем: в Калькулятор_ставки_часа.xlsx есть три диаграммы. openpyxl при
сохранении их теряет, поэтому книгу нельзя просто открыть и записать.
Здесь мы работаем с zip-архивом: все существующие части копируются
байт в байт, добавляется только новый лист.

Запуск:  python3 лист_в_книгу.py книга.xlsx 28_Журнал_изменений данные.tsv
Данные — TSV: первая строка заголовки, дальше строки. Всё пишется текстом
(inline strings), формул нет — пересчёт книги такой лист не затрагивает.
"""
import sys, os, re, shutil, zipfile, io

def экранировать(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

def буква(n):
    s = ''
    while n > 0:
        n, о = divmod(n - 1, 26)
        s = chr(65 + о) + s
    return s

def лист_xml(строки):
    r = []
    for i, ряд in enumerate(строки, 1):
        ячейки = ''.join(
            f'<c r="{буква(j)}{i}" t="inlineStr"><is><t xml:space="preserve">'
            f'{экранировать(v)}</t></is></c>'
            for j, v in enumerate(ряд, 1) if v != '')
        r.append(f'<row r="{i}">{ячейки}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetFormatPr defaultRowHeight="15"/>'
            '<cols><col min="1" max="1" width="14" customWidth="1"/>'
            '<col min="2" max="2" width="34" customWidth="1"/>'
            '<col min="3" max="6" width="46" customWidth="1"/></cols>'
            f'<sheetData>{"".join(r)}</sheetData></worksheet>')

def добавить(книга, имя_листа, строки):
    if len(имя_листа) > 31:
        raise SystemExit('имя листа длиннее 31 символа')
    времен = книга + '.новая'
    with zipfile.ZipFile(книга) as z:
        части = {n: z.read(n) for n in z.namelist()}
        порядок = z.namelist()

    wb = части['xl/workbook.xml'].decode('utf-8')
    if f'name="{имя_листа}"' in wb:
        raise SystemExit(f'лист «{имя_листа}» в книге уже есть')

    номера = [int(m) for m in re.findall(r'xl/worksheets/sheet(\d+)\.xml', ' '.join(порядок))]
    новый_номер = max(номера) + 1
    rels = части['xl/_rels/workbook.xml.rels'].decode('utf-8')
    rid = 'rId' + str(max(int(m) for m in re.findall(r'Id="rId(\d+)"', rels)) + 1)
    sheetid = max(int(m) for m in re.findall(r'sheetId="(\d+)"', wb)) + 1

    части[f'xl/worksheets/sheet{новый_номер}.xml'] = лист_xml(строки).encode('utf-8')
    части['xl/workbook.xml'] = wb.replace(
        '</sheets>',
        f'<sheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships" name="{экранировать(имя_листа)}" sheetId="{sheetid}" '
        f'state="visible" r:id="{rid}"/></sheets>'
    ).encode('utf-8')
    части['xl/_rels/workbook.xml.rels'] = rels.replace(
        '</Relationships>',
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{новый_номер}.xml"/></Relationships>'
    ).encode('utf-8')
    ct = части['[Content_Types].xml'].decode('utf-8')
    части['[Content_Types].xml'] = ct.replace(
        '</Types>',
        f'<Override PartName="/xl/worksheets/sheet{новый_номер}.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
    ).encode('utf-8')

    порядок = порядок + [f'xl/worksheets/sheet{новый_номер}.xml']
    with zipfile.ZipFile(времен, 'w', zipfile.ZIP_DEFLATED) as z:
        for имя in порядок:
            z.writestr(имя, части[имя])
    shutil.move(времен, книга)
    print(f'лист «{имя_листа}» добавлен: sheet{новый_номер}.xml')

if __name__ == '__main__':
    книга, имя, tsv = sys.argv[1], sys.argv[2], sys.argv[3]
    строки = [л.split('\t') for л in io.open(tsv, encoding='utf-8').read().rstrip('\n').split('\n')]
    добавить(книга, имя, строки)
