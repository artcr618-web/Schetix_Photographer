#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Удаляет строку d.core из старого 15_Реестр_полей без openpyxl.save().

Работает напрямую с OOXML ZIP, поэтому три диаграммы контрольной книги
сохраняются. Старые расчётные листы и формулы не изменяются.
"""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
import os

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'Книга' / 'Калькулятор_ставки_часа.xlsx'
M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
SHEET = 'xl/worksheets/sheet30.xml'  # 15_Реестр_полей; проверено через workbook.xml.rels

with ZipFile(BOOK, 'r') as zin:
    charts_before = sorted(x for x in zin.namelist() if x.startswith('xl/charts/chart'))
    xml = etree.fromstring(zin.read(SHEET))
    rows = xml.findall('.//{%s}row' % M)
    targets = []
    for row in rows:
        values = []
        for cell in row.findall('{%s}c' % M):
            values.extend(cell.xpath('.//*[local-name()="t"]/text()'))
        if any(v in ('RES-core', 'd.core', 'core') for v in values):
            targets.append(row)
    if len(targets) != 1 and len(targets) != 0:
        raise SystemExit(f'Ожидалась одна строка d.core, найдено {len(targets)}')
    if targets:
        targets[0].getparent().remove(targets[0])
    new_xml = etree.tostring(xml, xml_declaration=True, encoding='UTF-8', standalone=True)

    with NamedTemporaryFile(dir=BOOK.parent, suffix='.xlsx', delete=False) as f:
        tmp = Path(f.name)
    try:
        with ZipFile(tmp, 'w', ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = new_xml if item.filename == SHEET else zin.read(item.filename)
                zout.writestr(item, data)
        with ZipFile(tmp, 'r') as check:
            charts_after = sorted(x for x in check.namelist() if x.startswith('xl/charts/chart'))
            if charts_after != charts_before or len(charts_after) != 3:
                raise SystemExit('Диаграммы контрольной книги изменились')
        os.replace(tmp, BOOK)
    finally:
        tmp.unlink(missing_ok=True)

print('Строка d.core удалена из 15_Реестр_полей; 3 диаграммы сохранены')
