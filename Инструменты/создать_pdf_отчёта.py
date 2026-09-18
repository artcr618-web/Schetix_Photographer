#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создаёт три контрольных PDF report через headless Chromium.

Основной PDF: визуальный отчёт + детализация, без справочника.
Отдельно: справочник и детализация. При отсутствии Chromium устанавливает его.
"""
from pathlib import Path
import re, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'Веб'/'report.html'
OUT=Path(sys.argv[1]).expanduser().resolve() if len(sys.argv)>1 else ROOT/'PDF'
OUT.mkdir(parents=True,exist_ok=True)

chrome=next((shutil.which(x) for x in ('chromium','chromium-browser','google-chrome') if shutil.which(x)),None)
if not chrome:
    subprocess.check_call(['sudo','apt-get','update','-qq'])
    subprocess.check_call(['sudo','apt-get','install','-y','-qq','--no-install-recommends','chromium','poppler-utils'])
    chrome=shutil.which('chromium')
if not chrome:raise SystemExit('Chromium не найден')

jobs={
 'main':'Счётикс_основной_отчёт_демо.pdf',
 'glossary':'Счётикс_справочник_демо.pdf',
 'details':'Счётикс_детализация_демо.pdf',
}
minimum={'main':12,'glossary':8,'details':3}
for mode,name in jobs.items():
    target=OUT/name
    url=REPORT.resolve().as_uri()+f'?demo=1&print={mode}'
    cmd=[chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
         '--no-pdf-header-footer','--run-all-compositor-stages-before-draw',
         '--virtual-time-budget=5000',f'--print-to-pdf={target}',url]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode or not target.exists():raise SystemExit(f'{mode}: Chromium не создал PDF\n{p.stderr[-500:]}')
    data=target.read_bytes(); pages=len(re.findall(rb'/Type\s*/Page\b',data))
    a4=bool(re.search(rb'/MediaBox\s*\[0 0 841\.[0-9]+ 594\.[0-9]+\]',data))
    if not data.startswith(b'%PDF') or not a4 or pages<minimum[mode]:
        raise SystemExit(f'{mode}: некорректный PDF, pages={pages}, A4={a4}, size={len(data)}')
    print(f'✓ {mode}: {pages} стр. · A4 · {len(data)} байт · {target.relative_to(ROOT)}')
