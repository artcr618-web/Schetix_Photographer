#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создаёт контрольный PDF прайса (PDF/Счётикс_прайс_демо.pdf) через headless Chromium.

Правило владельца 07.09.2026 (Документация/ПРАВИЛО_ТРИ_ВИДА_ПРАЙСА.md):
контрольный PDF — это тот же слепок, что режим «Просмотр» и печать из
price.html, собранный по адресу price.html?print=1&demo=1. Вручную из
браузера PDF в папку PDF/ не кладётся — только этим скриптом.

Запуск из корня репозитория:  python3 Инструменты/создать_pdf_прайса.py [папка_вывода]
Браузер: системный chromium/google-chrome, иначе Chromium из Playwright
(~/.cache/ms-playwright), иначе — установка chromium через apt (как в
создать_pdf_отчёта.py).
"""
from pathlib import Path
import glob, os, re, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
PRICE = ROOT / 'Веб' / 'price.html'
OUT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else ROOT / 'PDF'
OUT.mkdir(parents=True, exist_ok=True)
NAME = 'Счётикс_прайс_демо.pdf'
MIN_PAGES = 2   # обложка + таблицы + доп. услуги: меньше двух листов быть не может

def найти_браузер():
    for x in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable'):
        p = shutil.which(x)
        if p: return p
    домашняя = os.path.expanduser('~/.cache/ms-playwright')
    for шаблон in ('chromium-*/chrome-linux*/chrome', 'chromium_headless_shell-*/chrome-linux*/headless_shell'):
        найдено = sorted(glob.glob(os.path.join(домашняя, шаблон)))
        if найдено: return найдено[-1]
    return None

chrome = найти_браузер()
if not chrome:
    subprocess.check_call(['sudo', 'apt-get', 'update', '-qq'])
    subprocess.check_call(['sudo', 'apt-get', 'install', '-y', '-qq', '--no-install-recommends', 'chromium', 'poppler-utils'])
    chrome = shutil.which('chromium')
if not chrome: raise SystemExit('Chromium не найден')

target = OUT / NAME
url = PRICE.resolve().as_uri() + '?print=1&demo=1'
cmd = [chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
       '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
       '--virtual-time-budget=5000', f'--print-to-pdf={target}', url]
p = subprocess.run(cmd, capture_output=True, text=True)
if p.returncode or not target.exists():
    raise SystemExit(f'прайс: Chromium не создал PDF\n{p.stderr[-500:]}')

data = target.read_bytes()
pages = len(re.findall(rb'/Type\s*/Page\b', data))
# A4 портрет: 595×842 pt (Chromium пишет 594.96 × 841.92)
a4 = bool(re.search(rb'/MediaBox\s*\[0 0 59[45]\.[0-9]+ 84[12]\.[0-9]+\]', data))
if not data.startswith(b'%PDF') or not a4 or pages < MIN_PAGES:
    raise SystemExit(f'прайс: некорректный PDF, pages={pages}, A4 портрет={a4}, size={len(data)}')
print(f'✓ прайс: {pages} стр. · A4 портрет · {len(data)} байт · {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}')
