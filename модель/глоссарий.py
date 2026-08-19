# -*- coding: utf-8 -*-
"""ГЛОССАРИЙ: один источник — таблица, лист 01_Глоссарий книги.

Порядок работы
--------------
1. Правку вносим В ТАБЛИЦУ — лист `01_Глоссарий`. Только там живут данные.
2. `python3 модель/глоссарий.py` — перестраивает `модель/глоссарий.html`.
   Это та же таблица, сделанная для чтения глазами. В книгу скрипт при
   этом НИЧЕГО не пишет.
3. Потом перестраиваем служебные скрипты, чтобы правка дошла до
   калькулятора: `web/части/справочник_в_отчёт.py`, `подсказки.py`, `демо.py`,
   и проверяем `ДОКУМЕНТАЦИЯ/4_инструменты/проверить.py`.

Запись в таблицу — отдельным действием и только по прямой команде:
`python3 модель/глоссарий.py --в-таблицу` — приводит лист к единой разметке
и вписывает пересчитанные служебные столбцы (№, где используется, сверка).

Все разделы одного вида: одинаковые столбцы, одинаковый порядок. Служебные
понятия, типы полей, блоки отчёта, понятия справочника — такие же таблицы.

Единая разметка столбцов:
  № · Наименование · ID · Тип · Определение · Определение утверждено ·
  Описание алгоритма · Формула (пример расчёта) · Где используется ·
  Решение (временный) · Справочник · для сверки (временный)

Правки: вносим прямо в лист книги (скриптом или руками в Excel), потом
`python3 модель/глоссарий.py` — он пересчитает и перерисует обе стороны.

Запуск: python3 модель/глоссарий.py
"""
import re, html, importlib.util, unicodedata, datetime, shutil, zipfile
import openpyxl

КОРЕНЬ = '/home/user/schetix'
# Структура анкеты и книги живёт на своих листах (07_Интерфейс, 08_UI,
# 03_Каталоги) — в глоссарии понятий ей не место.
УБРАТЬ_РАЗДЕЛЫ = ('A2 ·', 'A3 ·', 'A4 ·')
КНИГА = КОРЕНЬ + '/Калькулятор_ставки_часа.xlsx'
ЛИСТ = '01_Глоссарий'

ШАПКА = ['№', 'Наименование', 'Статус (временный)',
         'Справочник · для сверки (временный)', 'ID', 'Тип', 'Определение',
         'Определение утверждено', 'Описание алгоритма', 'Формула (пример расчёта)',
         'Где используется', 'Решение (временный)']
ПОЛЯ = ['имя', 'статус', 'свер', 'ид', 'тип', 'опред', 'утв', 'алго', 'форм',
        'где', 'решение']

# ── справочник сайта: единственный источник названий, видимых человеку ──
спец = importlib.util.spec_from_file_location('тп', КОРЕНЬ + '/web/части/таблицы_прототип.py')
мод = importlib.util.module_from_spec(спец)
try: спец.loader.exec_module(мод)
except SystemExit: pass
СПР = мод.СПРАВОЧНИК


def ключ(с):
    с = unicodedata.normalize('NFKC', str(с)).lower().replace('ё', 'е')
    с = re.sub(r'\(.*?\)', ' ', с)
    return re.sub(r'[^а-яa-z0-9]+', ' ', с).strip()


ИНДЕКС = {ключ(k): k for k in СПР}


def совпало(имя):
    к = ключ(имя)
    if к in ИНДЕКС: return ИНДЕКС[к]
    for эк, ор in ИНДЕКС.items():
        if к and (к == эк or к.startswith(эк + ' ') or эк.startswith(к + ' ')): return ор
    return None


ГДЕ_ЦВЕТ = {
    'внутренний': ('#FDE9EC', '#B3243B'),
    'общий': ('#E8F5EC', '#1B7F3B'),
    'для пользователя': ('#E7EFFB', '#1B4F9C'),
}
СТАТУС_ЦВЕТ = {
    'не сверяется': ('#F1F3F6', '#7A838F'),
    'тождественно': ('#E8F5EC', '#1B7F3B'),
    'переименовать': ('#FFF4E0', '#9A6400'),
    'нет понятия': ('#FDE9EC', '#B3243B'),
}

ВИДНО = None


def видимые_тексты():
    куски = []
    for ф in ('web/calc.html', 'web/report.html'):
        т = open(КОРЕНЬ + '/' + ф, encoding='utf-8').read()
        скрипты = '\n'.join(re.findall(r'<script.*?</script>', т, flags=re.S))
        без = re.sub(r'<script.*?</script>', ' ', т, flags=re.S)
        без = re.sub(r'<style.*?</style>', ' ', без, flags=re.S)
        куски.append(re.sub(r'<[^>]+>', ' ', без))
        куски += [с for с in re.findall(r'''['"`]([^'"`\n]{3,200})['"`]''', скрипты)
                  if re.search(r'[А-Яа-яЁё]', с)]
    return ключ(' '.join(куски))


def где(с, термин):
    global ВИДНО
    if ВИДНО is None: ВИДНО = видимые_тексты()
    тип = str(с.get('тип') or '').lower()
    if тип in ('служебное', 'meta', 'ui'): return 'внутренний'
    считается = тип in ('calc', 'default', 'const', 'switch')
    показан = bool(термин)
    if not показан:
        к = ключ(с['имя'])
        показан = len(к) > 3 and к in ВИДНО
    if показан and считается: return 'общий'
    if показан: return 'для пользователя'
    return 'внутренний'


# ══ ЧТЕНИЕ ЛИСТА ═════════════════════════════════════════════════════
ЗАГОЛОВКИ = {
    '№': 'номер', 'наименование': 'имя', 'id': 'ид', 'тип': 'тип',
    'определение': 'опред', 'определение утверждено': 'утв',
    'описание алгоритма': 'алго', 'формула (пример расчёта)': 'форм',
    'формула / значение': 'форм', 'описание': 'опред',
    'где используется': 'где', 'решение (временный)': 'решение',
    'решение': 'решение', 'справочник · для сверки (временный)': 'свер',
    'статус (временный)': 'статус',
}


def читать():
    """Читает лист по ЗАГОЛОВКАМ столбцов, а не по их номерам.

    Поэтому порядок столбцов можно менять как угодно — и старую разметку
    (Наименование · ID · Тип · Описание · Формула) скрипт тоже понимает.
    """
    кн = openpyxl.load_workbook(КНИГА, data_only=True)
    ws = кн[ЛИСТ]
    строки = [list(r) for r in ws.iter_rows(values_only=True)]

    карта = None
    разделы, текущий = [], None
    for r in строки:
        зн = [(str(c).strip() if c is not None else '') for c in r]
        нижние = [x.lower() for x in зн]
        # строка-шапка: в ней встречается «наименование»
        if 'наименование' in нижние or 'термин' in нижние:
            карта = {}
            for i, з in enumerate(нижние):
                поле = ЗАГОЛОВКИ.get(з)
                if поле and поле not in карта.values(): карта[i] = поле
            continue
        текст = зн[0] if зн else ''
        прочее = [x for x in зн[1:] if x]
        if not текст and not прочее: continue
        if текст and not прочее:
            if len(текст) > 110: continue
            текущий = {'имя': текст, 'строки': []}
            разделы.append(текущий)
            continue
        if текущий is None:
            текущий = {'имя': 'Без раздела', 'строки': []}
            разделы.append(текущий)
        с = {п: '' for п in ('имя', 'ид', 'тип', 'опред', 'утв', 'алго', 'форм',
                             'где', 'решение', 'свер', 'статус')}
        if карта:
            for i, поле in карта.items():
                if поле == 'номер' or i >= len(зн): continue
                с[поле] = зн[i]
        else:
            с['имя'], с['ид'], с['тип'], с['опред'] = (зн + [''] * 5)[:4]
            с['форм'] = (зн + [''] * 5)[4]
        if not с['имя']: continue
        с['раздел'] = текущий['имя']
        текущий['строки'].append(с)
    return [р for р in разделы if р['строки']
            and not р['имя'].startswith(УБРАТЬ_РАЗДЕЛЫ)]


def пересчитать(разделы):
    н = 0
    for р in разделы:
        for с in р['строки']:
            н += 1
            с['№'] = н
            ручной = (с.get('свер') or '').split(' — ')[0].strip()
            термин = совпало(с['имя']) or (ручной if ручной in СПР else None)
            с['где'] = где(с, термин)
            if с['где'] == 'внутренний':
                с['статус'], с['термин'] = 'не сверяется', None
            elif термин:
                с['статус'] = 'тождественно' if совпало(с['имя']) else 'переименовать'
                с['термин'] = термин
            else:
                с['статус'], с['термин'] = 'нет понятия', None
            с['свер'] = f"{с['термин']} — {СПР[с['термин']]}" if с['термин'] else ''
            if not с['утв']: с['утв'] = 'черновик' if с['опред'] else ''
    return разделы


# ══ ЗАПИСЬ ЛИСТА ═════════════════════════════════════════════════════
def экр(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def буква(n):
    s = ''
    while n > 0:
        n, о = divmod(n - 1, 26)
        s = chr(65 + о) + s
    return s


def писать(разделы):
    из = [['01 · ГЛОССАРИЙ — единый реестр понятий, параметров и обозначений'],
          ['Собирается вместе с модель/глоссарий.html одним скриптом модель/глоссарий.py. '
           'Источник — этот лист. Столбцы «Решение» и «Справочник» временные.'],
          []]
    for р in разделы:
        из.append([р['имя']])
        из.append(ШАПКА)
        for с in р['строки']:
            из.append([str(с['№'])] + [с.get(п, '') for п in ПОЛЯ])
        из.append([])

    ряды = []
    for i, ряд in enumerate(из, 1):
        яч = ''.join(
            f'<c r="{буква(j)}{i}" t="inlineStr"><is><t xml:space="preserve">'
            f'{экр(v)}</t></is></c>'
            for j, v in enumerate(ряд, 1) if str(v) != '')
        ряды.append(f'<row r="{i}">{яч}</row>')
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<sheetFormatPr defaultRowHeight="15"/>'
           '<cols><col min="1" max="1" width="6" customWidth="1"/>'
           '<col min="2" max="2" width="34" customWidth="1"/>'
           '<col min="3" max="3" width="16" customWidth="1"/>'
           '<col min="4" max="4" width="40" customWidth="1"/>'
           '<col min="5" max="6" width="16" customWidth="1"/>'
           '<col min="7" max="7" width="60" customWidth="1"/>'
           '<col min="8" max="8" width="16" customWidth="1"/>'
           '<col min="9" max="9" width="60" customWidth="1"/>'
           '<col min="10" max="10" width="38" customWidth="1"/>'
           '<col min="11" max="12" width="26" customWidth="1"/></cols>'
           f'<sheetData>{"".join(ряды)}</sheetData></worksheet>')

    shutil.copy(КНИГА, КНИГА + '.до_глоссария')
    with zipfile.ZipFile(КНИГА) as z:
        части = {n: z.read(n) for n in z.namelist()}
        порядок = z.namelist()
    wb = части['xl/workbook.xml'].decode()
    rels = части['xl/_rels/workbook.xml.rels'].decode()
    rid = {}
    for кусок in re.findall(r'<Relationship\b[^>]*/>', rels):
        i = re.search(r'Id="([^"]+)"', кусок); t = re.search(r'Target="([^"]+)"', кусок)
        if i and t: rid[i.group(1)] = t.group(1)
    лист = dict(re.findall(r'name="([^"]+)"[^>]*r:id="([^"]+)"', wb))[ЛИСТ]
    цель = rid[лист]
    путь = цель.lstrip('/') if цель.startswith('/') else 'xl/' + цель
    части[путь] = xml.encode()
    with zipfile.ZipFile(КНИГА, 'w', zipfile.ZIP_DEFLATED) as z:
        for имя in порядок:
            z.writestr(имя, части[имя])
    всего = sum(len(р['строки']) for р in разделы)
    print(f'лист {ЛИСТ}: {len(разделы)} разделов, {всего} строк, {len(ШАПКА)} столбцов')


# ══ HTML ═════════════════════════════════════════════════════════════
def э(x):
    return html.escape(str(x)) if x not in (None, '') else '—'


def рисовать(разделы):
    все = [с for р in разделы for с in р['строки']]
    счёт = {к: sum(1 for с in все if с['статус'] == к) for к in СТАТУС_ЦВЕТ}
    счёт_где = {к: sum(1 for с in все if с['где'] == к) for к in ГДЕ_ЦВЕТ}
    сверяем = [с for с in все if с['где'] != 'внутренний']

    o = ['''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Глоссарий — Счётикс</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:32px 28px 80px;background:#F6F7F9;color:#1D2530;
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
h1{margin:0 0 6px;font-size:26px;letter-spacing:-.02em}
h2{margin:38px 0 12px;font-size:20px;letter-spacing:-.01em}
.под{color:#6A7482;font-size:14px;margin:0 0 18px;max-width:74em}
.сводка{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 8px}
.карта{background:#fff;border:1px solid #E2E6EC;border-radius:12px;padding:12px 16px;min-width:150px}
.карта b{display:block;font-size:22px;line-height:1.2}
.карта span{font-size:13px;color:#6A7482}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #E2E6EC;
border-radius:12px;overflow:hidden;margin-bottom:8px}
th{background:#F0F2F5;text-align:left;font-size:12.5px;text-transform:uppercase;
letter-spacing:.04em;color:#5B6673;padding:9px 12px;border-bottom:1px solid #E2E6EC;font-weight:600}
td{padding:10px 12px;border-bottom:1px solid #EEF0F3;vertical-align:top;font-size:14px}
tr:last-child td{border-bottom:0}
td.ном{width:46px;color:#9AA3AE;font-size:13px;font-variant-numeric:tabular-nums}
td.имя{font-weight:600;width:220px}
td.ид{width:140px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:#7A838F}
td.тип{width:90px;color:#7A838F;font-size:12.5px}
td.опр{color:#3A4553;width:300px}
td.алго{width:280px;color:#3A4553;font-size:13.5px}
td.форм{width:180px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:#5B6673}
td.решение{width:150px;color:#3A4553;font-size:13px}
.мет{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.ждём{color:#C3C9D1;font-style:italic}
.из{display:block;margin-top:4px;font-size:12px;font-weight:600}
th.врем,td.врем{background:#FAFBFC;border-left:2px dashed #D8DDE4}
th.врем{font-style:italic}
.фильтры{position:sticky;top:0;z-index:5;background:#F6F7F9;padding:10px 0 12px;margin-bottom:4px;
border-bottom:1px solid #E2E6EC}
.фильтры button{margin:0 8px 6px 0;padding:7px 14px;border:1px solid #D5DAE1;background:#fff;
border-radius:20px;font:inherit;font-size:13.5px;cursor:pointer}
.фильтры button.вкл{background:#1D2530;color:#fff;border-color:#1D2530}
.скрыт{display:none}
</style></head><body>''']
    o.append('<h1>Глоссарий</h1>')
    o.append('<p class="под">Один источник — лист <code>01_Глоссарий</code> книги. '
             'Этот документ и лист собираются одним скриптом и всегда совпадают. '
             'Все разделы одного вида: одинаковые столбцы, одинаковый порядок. '
             'Столбцы «Решение» и «Справочник» отчёркнуты пунктиром — они временные '
             'и удаляются, когда всё согласовано.</p>')

    o.append('<div class="сводка">')
    o.append(f'<div class="карта"><b>{len(все)}</b><span>строк всего</span></div>')
    o.append(f'<div class="карта"><b>{len(разделы)}</b><span>разделов</span></div>')
    o.append(f'<div class="карта"><b>{len(сверяем)}</b><span>сверяются</span></div>')
    for к, (фон, цвет) in СТАТУС_ЦВЕТ.items():
        o.append(f'<div class="карта" style="background:{фон}"><b style="color:{цвет}">{счёт[к]}</b>'
                 f'<span>{к}</span></div>')
    o.append('</div><div class="сводка">')
    for к, (фон, цвет) in ГДЕ_ЦВЕТ.items():
        o.append(f'<div class="карта" style="background:{фон}"><b style="color:{цвет}">{счёт_где[к]}</b>'
                 f'<span>{к}</span></div>')
    o.append('</div>')

    o.append('<div class="фильтры"><button class="вкл" data-ф="все">Показать всё</button>')
    for к in СТАТУС_ЦВЕТ: o.append(f'<button data-ф="{к}">{к}</button>')
    for к, (фон, цвет) in ГДЕ_ЦВЕТ.items():
        o.append(f'<button data-ф="{к}" style="background:{фон};color:{цвет};border-color:{фон}">{к}</button>')
    o.append('<button data-ф="справочник" style="background:#EFE8FB;color:#5B34A8;'
             'border-color:#EFE8FB">только справочник</button>')
    o.append('</div>')

    for р in разделы:
        o.append(f'<h2>{э(р["имя"])}</h2>')
        o.append('<table><tr><th>№</th><th>Наименование</th>'
                 '<th class="врем">Статус <i>(на удаление)</i></th>'
                 '<th class="врем">Справочник · для сверки <i>(на удаление)</i></th>'
                 '<th>ID</th><th>Тип</th>'
                 '<th>Определение</th><th>Описание алгоритма</th>'
                 '<th>Формула (пример расчёта)</th><th>Где используется</th>'
                 '<th class="врем">Решение <i>(на удаление)</i></th></tr>')
        for с in р['строки']:
            гфон, гцвет = ГДЕ_ЦВЕТ[с['где']]
            сфон, сцвет = СТАТУС_ЦВЕТ[с['статус']]
            кл = ' class="строка-нет"' if с['статус'] == 'нет понятия' else ''
            опред = э(с['опред'])
            if с['опред']:
                цв = '#1B7F3B' if с['утв'] == 'согласовано' else '#9A6400'
                опред += f'<span class="из" style="color:{цв}">{э(с["утв"])}</span>'
            алго = э(с['алго']) if с['алго'] else '<span class="ждём">описать словами</span>'
            реш = f'<b>{э(с["решение"])}</b>' if с['решение'] else '—'
            вспр = 'да' if с['термин'] or с['раздел'].startswith('Z ·') else 'нет'
            o.append(f'<tr{кл} data-с="{с["статус"]}" data-г="{с["где"]}" data-сп="{вспр}">'
                     f'<td class="ном">{с["№"]}</td><td class="имя">{э(с["имя"])}</td>'
                     f'<td class="врем"><span class="мет" style="background:{сфон};color:{сцвет}">'
                     f'{с["статус"]}</span></td>'
                     f'<td class="опр врем">{э(с["свер"])}</td>'
                     f'<td class="ид">{э(с["ид"])}</td><td class="тип">{э(с["тип"])}</td>'
                     f'<td class="опр">{опред}</td><td class="алго">{алго}</td>'
                     f'<td class="форм">{э(с["форм"])}</td>'
                     f'<td><span class="мет" style="background:{гфон};color:{гцвет}">{с["где"]}</span></td>'
                     f'<td class="решение врем">{реш}</td></tr>')
        o.append('</table>')

    o.append(f'<p class="под" style="margin-top:34px">Собрано {datetime.date.today():%d.%m.%Y}</p>')
    o.append('''<script>
document.querySelectorAll('.фильтры button').forEach(function(б){
  б.onclick=function(){
    document.querySelectorAll('.фильтры button').forEach(function(x){x.classList.remove('вкл')});
    б.classList.add('вкл');
    var ф=б.getAttribute('data-ф');
    document.querySelectorAll('tr[data-с]').forEach(function(тр){
      var ок = ф==='все' || тр.getAttribute('data-с')===ф || тр.getAttribute('data-г')===ф
               || (ф==='справочник' && тр.getAttribute('data-сп')==='да');
      тр.classList.toggle('скрыт', !ок);
    });
    document.querySelectorAll('table').forEach(function(т){
      var всего=т.querySelectorAll('tr[data-с]').length;
      var видно=т.querySelectorAll('tr[data-с]:not(.скрыт)').length;
      var пусто = всего>0 && видно===0;
      т.classList.toggle('скрыт', пусто);
      var h=т.previousElementSibling;
      if(h&&h.tagName==='H2')h.classList.toggle('скрыт', пусто);
    });
  };
});
</script></body></html>''')
    return '\n'.join(o)


if __name__ == '__main__':
    import sys
    разделы = пересчитать(читать())
    if '--в-таблицу' in sys.argv:
        писать(разделы)
    путь = КОРЕНЬ + '/модель/глоссарий.html'
    open(путь, 'w', encoding='utf-8').write(рисовать(разделы))
    print('глоссарий собран из таблицы:', путь)
    if '--в-таблицу' not in sys.argv:
        print('в книгу не писали. Нужно — запустите с ключом --в-таблицу')
