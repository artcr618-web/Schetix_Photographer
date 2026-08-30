#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает проверяемую капсулу передачи Счётикса в новую сессию.

Архив не заменяет живую рабочую папку автоматически. Он содержит инструкции,
текущую точку, рабочие проводники, активные задачи, критический код, книгу и
инструменты проверки. Старый архив и тяжёлые изображения намеренно исключены.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'Документация' / 'Переезд_между_сессиями'
OUT = ROOT / 'Архив' / 'Передача_между_сессиями'
MANIFEST = DOC / 'МАНИФЕСТ.json'

fixed = [
    'README.md',
    'Документация/00_АЛГОРИТМ_ВЗАИМОДЕЙСТВИЯ_И_ТЕКУЩАЯ_СТАДИЯ.md',
    'Документация/АЛГОРИТМЫ.md',
    'Документация/ДОРОЖНАЯ_КАРТА.md',
    'Документация/Описания расчётов/00_РЕЕСТР_РАСЧЁТОВ.md',
    'Документация/Описания расчётов/Архитектура — Правила модели и интерфейса.md',
    'Документация/Описания расчётов/Архитектура — Нулевые значения, отключённые блоки и убыток.md',
    'Задачи/РЕЕСТР.md',
    'Веб/calc.html',
    'Веб/report.html',
    'Веб/Части/каркас.html',
    'Книга/Калькулятор_ставки_часа.xlsx',
    'Инструменты/карта.py',
    'Инструменты/демо.py',
    'Инструменты/проверить.py',
    'Инструменты/проверить_report_headless.js',
    'Инструменты/создать_pdf_отчёта.py',
    'package.json',
    'package-lock.json',
    'PDF/Счётикс_основной_отчёт_демо.pdf',
    'PDF/Счётикс_справочник_демо.pdf',
    'PDF/Счётикс_детализация_демо.pdf',
    'Инструменты/харнесс.js',
    'Инструменты/сверить_глоссарий.py',
    'Инструменты/проверить_сценарии_чистой_книги.py',
    'Инструменты/собрать_передачу_сессии.py',
]

files = [ROOT / x for x in fixed]
files += sorted(DOC.glob('*.md'))
files += sorted((ROOT / 'Задачи').glob('З-*.md'))
# Закрытые задачи нужны для восстановления причин решений, но не как текущая истина.
files += sorted((ROOT / 'Архив' / 'Задачи').glob('З-*.md'))
# Паспорта компактны и нужны для восстановления причин текущего расчёта.
files += sorted((ROOT / 'Документация' / 'Описания расчётов').glob('*.md'))

# Уникальность с сохранением порядка.
seen, unique = set(), []
for path in files:
    path = path.resolve()
    if path in seen:
        continue
    seen.add(path); unique.append(path)
files = unique

missing = [str(p.relative_to(ROOT)) for p in files if not p.is_file()]
if missing:
    raise SystemExit('Не найдены обязательные файлы:\n' + '\n'.join(missing))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def command(args, default='не определено'):
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return default

now = datetime.now(ZoneInfo('Europe/Moscow'))
entries = []
for path in files:
    rel = path.relative_to(ROOT).as_posix()
    entries.append({'path': rel, 'size': path.stat().st_size, 'sha256': sha(path)})

manifest = {
    'schema': 1,
    'product': 'Счётикс',
    'purpose': 'Передача знаний и точки продолжения между сессиями',
    'created_at': now.isoformat(timespec='seconds'),
    'root_hint': '/home/user/Schetix_Photographer',
    'start_file': 'Документация/Переезд_между_сессиями/00_НАЧАТЬ_ЗДЕСЬ.md',
    'prompts_file': 'Документация/Переезд_между_сессиями/02_ПРОМПТЫ_ДЛЯ_НОВОЙ_СЕССИИ.md',
    'continuation_file': 'Документация/Переезд_между_сессиями/ТОЧКА_ПРОДОЛЖЕНИЯ.md',
    'git_head': command(['git', 'rev-parse', 'HEAD']),
    'working_tree_changes': int(command(['bash', '-lc', 'git status --porcelain | wc -l'], '0') or 0),
    'warning': 'Не перезаписывать живую папку архивом без сравнения; архивные исторические документы не являются текущим источником.',
    'files': entries,
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Манифест должен описывать себя только на уровне пути; самохеширование невозможно.
manifest_bytes = MANIFEST.read_bytes()
OUT.mkdir(parents=True, exist_ok=True)
dated = OUT / f'Счётикс_передача_{now:%Y-%m-%d_%H-%M}.zip'
latest = OUT / 'Счётикс_передача_АКТУАЛЬНАЯ.zip'

for target in (dated, latest):
    tmp = target.with_suffix('.tmp')
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr('ПЕРЕДАЧА/МАНИФЕСТ.json', manifest_bytes)
        for path in files:
            z.write(path, 'ПЕРЕДАЧА/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(tmp, 'r') as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'Повреждена запись архива: {bad}')
    tmp.replace(target)

print('Передача собрана:')
print(' ', dated.relative_to(ROOT))
print(' ', latest.relative_to(ROOT))
print(f'Файлов: {len(files)}; размер: {latest.stat().st_size} байт; ZIP проверен')
