# -*- coding: utf-8 -*-
"""Переносит справочник из части/таблицы_прототип.py в отчёт.

Единственный источник — словарь СПРАВОЧНИК. Скрипт переписывает массив
`var REFD=[...]` в report.html и части/каркас.html, ничего больше не трогая.

Запуск: python3 web/части/справочник_в_отчёт.py
"""
import re, json, importlib.util

КОРЕНЬ = '/home/user/schetix'

спец = importlib.util.spec_from_file_location('тп', КОРЕНЬ + '/web/части/таблицы_прототип.py')
мод = importlib.util.module_from_spec(спец)
try: спец.loader.exec_module(мод)
except SystemExit: pass
СПР = мод.СПРАВОЧНИК

строки = [f'   {json.dumps([т, о], ensure_ascii=False)}'
          for т, о in sorted(СПР.items(), key=lambda п: п[0].lower())]
новый = 'var REFD=[\n' + ',\n'.join(строки) + '\n  ];'

# второй массив того же справочника — им пользуется детализация
спр_один = 'var \u0421\u041f\u0420 = ' + json.dumps(
    [[т, о] for т, о in sorted(СПР.items(), key=lambda п: п[0].lower())],
    ensure_ascii=False) + ';'
# карта «строка таблицы → запись справочника»
связь_один = 'var \u0421\u0412\u042f\u0417\u042c = ' + json.dumps(
    мод.СВЯЗЬ, ensure_ascii=False) + ';'

for файл in ('/web/report.html', '/web/части/каркас.html'):
    путь = КОРЕНЬ + файл
    т = open(путь, encoding='utf-8').read()
    сделано = []
    т, n1 = re.subn(r'var REFD=\[.*?\n *\];', новый, т, count=1, flags=re.S)
    сделано.append(('REFD', n1))
    т, n2 = re.subn(r'var \u0421\u041f\u0420 = \[.*?\];\n', спр_один + '\n', т, count=1, flags=re.S)
    сделано.append(('СПР', n2))
    т, n3 = re.subn(r'var \u0421\u0412\u042f\u0417\u042c = \{.*?\};\n', связь_один + '\n', т, count=1, flags=re.S)
    сделано.append(('СВЯЗЬ', n3))
    open(путь, 'w', encoding='utf-8').write(т)
    print(f'{файл} — {len(СПР)} записей · ' + ', '.join(f'{и}:{к}' for и, к in сделано))
