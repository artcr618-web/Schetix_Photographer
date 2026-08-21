# -*- coding: utf-8 -*-
"""ГЛОССАРИЙ: один источник — лист 01_Глоссарий книги.

Разметка (задана пользователем 19.08.2026):
  № · Наименование · ID · Назначение · Тип · Понятие ·
  Значение/формула · Описание алгоритма

Столбец «Тип» — ссылка на родителя: marker → data_type → ui.
Так выстроена иерархия обозначений.

Порядок работы
--------------
1. Правку вносим В ТАБЛИЦУ — лист `01_Глоссарий`.
2. `python3 модель/глоссарий.py` — перестраивает `модель/глоссарий.html`.
   В книгу при этом НИЧЕГО не пишет.
3. Запись в таблицу — только по прямой команде:
   `python3 модель/глоссарий.py --в-таблицу`
4. Потом служебные скрипты: `web/части/справочник_в_отчёт.py`,
   `подсказки.py`, `демо.py`. Проверка — `проверить.py`.
"""
import re, html, datetime, shutil, zipfile
import openpyxl

КОРЕНЬ = '/home/user/schetix'
КНИГА = КОРЕНЬ + '/Калькулятор_ставки_часа.xlsx'
ЛИСТ = '01_Глоссарий'

ШАПКА = ['№', 'Наименование', 'ID', 'Назначение', 'Тип', 'Понятие',
         'Значение/формула', 'Описание алгоритма']
ПОЛЯ = ['имя', 'ид', 'назначение', 'тип', 'понятие', 'знач', 'алго']

ЗАГОЛОВКИ = {
    '№': 'номер', 'наименование': 'имя', 'id': 'ид', 'назначение': 'назначение',
    'тип': 'тип', 'понятие': 'понятие', 'значение/формула': 'знач',
    'значение / формула': 'знач', 'описание алгоритма': 'алго',
}

ТИРЕ = '\u2014'


# ══ ЧТЕНИЕ ═══════════════════════════════════════════════════════════
def читать():
    """Читает лист по заголовкам столбцов, а не по их номерам."""
    ws = openpyxl.load_workbook(КНИГА, data_only=True)[ЛИСТ]
    карта, строки = None, []
    for r in ws.iter_rows(values_only=True):
        зн = [(str(c).strip() if c is not None else '') for c in r]
        нижние = [x.lower() for x in зн]
        if 'наименование' in нижние:
            карта = {i: ЗАГОЛОВКИ[з] for i, з in enumerate(нижние) if з in ЗАГОЛОВКИ}
            continue
        if not any(зн): continue
        if карта is None: continue                    # шапка листа и подпись
        с = {п: '' for п in ПОЛЯ}
        for i, поле in карта.items():
            if поле == 'номер' or i >= len(зн): continue
            с[поле] = зн[i]
        if not с['имя']: continue
        строки.append(с)
    return строки


def пересчитать(строки):
    for н, с in enumerate(строки, 1):
        с['№'] = н
        for п in ('знач', 'алго'):
            if not с[п]: с[п] = ТИРЕ
    return строки


# ══ ЗАПИСЬ ЛИСТА ═════════════════════════════════════════════════════
def экр(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def буква(n):
    s = ''
    while n > 0:
        n, о = divmod(n - 1, 26)
        s = chr(65 + о) + s
    return s


def писать(строки):
    из = [['01 · ГЛОССАРИЙ — понятия, обозначения и типы'],
          ['Источник данных. Собирается вместе с модель/глоссарий.html '
           'скриптом модель/глоссарий.py'],
          [],
          ШАПКА]
    for с in строки:
        из.append([str(с['№'])] + [с.get(п, '') for п in ПОЛЯ])

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
           '<col min="3" max="3" width="20" customWidth="1"/>'
           '<col min="4" max="5" width="14" customWidth="1"/>'
           '<col min="6" max="6" width="70" customWidth="1"/>'
           '<col min="7" max="7" width="24" customWidth="1"/>'
           '<col min="8" max="8" width="60" customWidth="1"/></cols>'
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
    print(f'лист {ЛИСТ}: {len(строки)} строк, {len(ШАПКА)} столбцов')


# ══ HTML ═════════════════════════════════════════════════════════════
def э(x):
    return html.escape(str(x)) if x not in (None, '') else ТИРЕ


ЦВЕТ_ТИПА = {
    'marker': ('#EFE8FB', '#5B34A8'),
    'data_type': ('#E7EFFB', '#1B4F9C'),
    'ui': ('#E8F5EC', '#1B7F3B'),
}


def рисовать(строки):
    типы = sorted({с['тип'] for с in строки if с['тип']})
    без_понятия = [с for с in строки if not с['понятие']]

    o = ['''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Глоссарий — Счётикс</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:32px 28px 80px;background:#F6F7F9;color:#1D2530;
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
h1{margin:0 0 6px;font-size:26px;letter-spacing:-.02em}
.под{color:#6A7482;font-size:14px;margin:0 0 18px;max-width:74em}
.сводка{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 8px}
.карта{background:#fff;border:1px solid #E2E6EC;border-radius:12px;padding:12px 16px;min-width:140px}
.карта b{display:block;font-size:22px;line-height:1.2}
.карта span{font-size:13px;color:#6A7482}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #E2E6EC;
border-radius:12px;overflow:hidden;margin-bottom:8px}
th{background:#2C3648;color:#fff;text-align:left;font-size:12.5px;padding:10px 12px;font-weight:600}
td{padding:10px 12px;border-bottom:1px solid #EEF0F3;vertical-align:top;font-size:14px}
tr:last-child td{border-bottom:0}
td.ном{width:44px;color:#9AA3AE;font-size:13px;font-variant-numeric:tabular-nums}
td.имя{font-weight:600;width:210px}
td.ид{width:150px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:#7A838F}
td.наз{width:100px;color:#7A838F;font-size:12.5px}
td.пон{color:#3A4553}
td.знач{width:150px;color:#5B6673;font-size:13px}
td.алго{width:230px;color:#3A4553;font-size:13.5px}
.мет{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600}
.нет td{background:#FFFBFC}
.фильтры{position:sticky;top:0;z-index:5;background:#F6F7F9;padding:10px 0 12px;
border-bottom:1px solid #E2E6EC;margin-bottom:10px}
.фильтры button{margin:0 8px 6px 0;padding:7px 14px;border:1px solid #D5DAE1;background:#fff;
border-radius:20px;font:inherit;font-size:13.5px;cursor:pointer}
.фильтры button.вкл{background:#1D2530;color:#fff;border-color:#1D2530}
.скрыт{display:none}
</style></head><body>''']
    o.append('<h1>Глоссарий</h1>')
    o.append('<p class="под">Источник — лист <code>01_Глоссарий</code> книги. '
             'Столбец «Тип» показывает, к чему относится обозначение: '
             '<b>marker</b> — маркер, <b>data_type</b> — тип данных, '
             '<b>ui</b> — элемент интерфейса.</p>')

    o.append('<div class="сводка">')
    o.append(f'<div class="карта"><b>{len(строки)}</b><span>строк</span></div>')
    for т in типы:
        н = sum(1 for с in строки if с['тип'] == т)
        фон, цвет = ЦВЕТ_ТИПА.get(т, ('#F1F3F6', '#5B6673'))
        o.append(f'<div class="карта" style="background:{фон}">'
                 f'<b style="color:{цвет}">{н}</b><span>{э(т)}</span></div>')
    o.append(f'<div class="карта" style="background:#FDE9EC">'
             f'<b style="color:#B3243B">{len(без_понятия)}</b>'
             f'<span>без понятия</span></div>')
    o.append('</div>')

    o.append('<div class="фильтры"><button class="вкл" data-ф="все">Показать всё</button>')
    for т in типы:
        фон, цвет = ЦВЕТ_ТИПА.get(т, ('#F1F3F6', '#5B6673'))
        o.append(f'<button data-ф="{э(т)}" style="background:{фон};color:{цвет};'
                 f'border-color:{фон}">{э(т)}</button>')
    o.append('<button data-ф="без">без понятия</button></div>')

    o.append('<table><tr>' + ''.join(f'<th>{з}</th>' for з in ШАПКА) + '</tr>')
    for с in строки:
        фон, цвет = ЦВЕТ_ТИПА.get(с['тип'], ('#F1F3F6', '#5B6673'))
        тип = (f'<span class="мет" style="background:{фон};color:{цвет}">{э(с["тип"])}</span>'
               if с['тип'] else ТИРЕ)
        кл = ' class="нет"' if not с['понятие'] else ''
        o.append(f'<tr{кл} data-т="{э(с["тип"])}" data-п="{"нет" if not с["понятие"] else "да"}">'
                 f'<td class="ном">{с["№"]}</td>'
                 f'<td class="имя">{э(с["имя"])}</td>'
                 f'<td class="ид">{э(с["ид"])}</td>'
                 f'<td class="наз">{э(с["назначение"])}</td>'
                 f'<td>{тип}</td>'
                 f'<td class="пон">{э(с["понятие"])}</td>'
                 f'<td class="знач">{э(с["знач"])}</td>'
                 f'<td class="алго">{э(с["алго"])}</td></tr>')
    o.append('</table>')
    o.append(f'<p class="под" style="margin-top:30px">Собрано {datetime.date.today():%d.%m.%Y}</p>')
    o.append('''<script>
document.querySelectorAll('.фильтры button').forEach(function(б){
  б.onclick=function(){
    document.querySelectorAll('.фильтры button').forEach(function(x){x.classList.remove('вкл')});
    б.classList.add('вкл');
    var ф=б.getAttribute('data-ф');
    document.querySelectorAll('tr[data-т]').forEach(function(тр){
      var ок = ф==='все' || тр.getAttribute('data-т')===ф
               || (ф==='без' && тр.getAttribute('data-п')==='нет');
      тр.classList.toggle('скрыт', !ок);
    });
  };
});
</script></body></html>''')
    return '\n'.join(o)


if __name__ == '__main__':
    import sys
    строки = пересчитать(читать())
    if '--в-таблицу' in sys.argv:
        писать(строки)
    путь = КОРЕНЬ + '/модель/глоссарий.html'
    open(путь, 'w', encoding='utf-8').write(рисовать(строки))
    print('глоссарий собран из таблицы:', путь)
    if '--в-таблицу' not in sys.argv:
        print('в книгу не писали. Нужно — запустите с ключом --в-таблицу')
