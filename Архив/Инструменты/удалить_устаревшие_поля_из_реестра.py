#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Удаляет устаревшие поля из 15_Реестр_полей ZIP-способом с диаграммами."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree
import os
ROOT=Path(__file__).resolve().parents[1]; BOOK=ROOT/'Книга'/'Калькулятор_ставки_часа.xlsx'
SHEET='xl/worksheets/sheet30.xml'; M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
with ZipFile(BOOK,'r') as zin:
    charts=[x for x in zin.namelist() if x.startswith('xl/charts/chart')]
    xml=etree.fromstring(zin.read(SHEET)); targets=[]
    fields={'d.sAuto','d.equip','d.promoM','d.current','d.side'}
    for row in xml.findall('.//{%s}row'%M):
        texts=[]
        for cell in row.findall('{%s}c'%M): texts += cell.xpath('.//*[local-name()="t"]/text()')
        if fields.intersection(texts): targets.append(row)
    for row in targets: row.getparent().remove(row)
    data=etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
    with NamedTemporaryFile(dir=BOOK.parent,suffix='.xlsx',delete=False) as f: tmp=Path(f.name)
    try:
        with ZipFile(tmp,'w',ZIP_DEFLATED) as zout:
            for item in zin.infolist(): zout.writestr(item,data if item.filename==SHEET else zin.read(item.filename))
        with ZipFile(tmp) as check:
            after=[x for x in check.namelist() if x.startswith('xl/charts/chart')]
            if after!=charts or len(after)!=3: raise SystemExit('Диаграммы изменились')
        os.replace(tmp,BOOK)
    finally: tmp.unlink(missing_ok=True)
print(f'Устаревшие поля удалены из реестра: {len(targets)}; 3 диаграммы сохранены')
