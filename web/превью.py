#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Показывает один блок отдельной страницей — с настоящей палитрой,
настоящими стилями и настоящими цифрами.

    python3 превью.py card01

Кладёт результат в /home/user/_превью_card01.html
Скрипт отчёта подключается целиком, поэтому render() заполняет
все цифры демо-набором, как в полном отчёте. Обращения к элементам
других блоков не мешают: они просто ничего не находят.
"""
import io, os, re, sys

ЗДЕСЬ  = os.path.dirname(os.path.abspath(__file__))
ЧАСТИ  = os.path.join(ЗДЕСЬ, 'части')
КАРКАС = os.path.join(ЧАСТИ, 'каркас.html')
ДОМ    = os.path.abspath(os.path.join(ЗДЕСЬ, '..'))


def читать(п):
    return io.open(п, encoding='utf-8').read()


def главное():
    if len(sys.argv) < 2:
        блоки = sorted(f[:-5] for f in os.listdir(ЧАСТИ)
                       if f.endswith('.html') and f != 'каркас.html')
        print('укажите блок. есть: ' + (', '.join(блоки) if блоки else '—'))
        return 1

    имя = sys.argv[1]
    путь = os.path.join(ЧАСТИ, имя + '.html')
    if not os.path.exists(путь):
        print('нет файла ' + путь)
        return 1

    к = читать(КАРКАС)
    стили = к[к.index('<style>'):к.index('</style>') + 8]
    скрипт = к[к.index('<script>'):к.index('</script>') + 9]
    блок = читать(путь)

    # В превью присутствует только один блок. Обращения скрипта к узлам
    # других блоков подменяем «пустышкой», чтобы render() дошёл до конца
    # и заполнил цифры нашего блока по-настоящему.
    заглушка = (
        "var $=function(id){var e=document.getElementById(id);if(e)return e;"
        "var f=document.createElement('div');f.__нет=1;return f};\n"
    )
    скрипт = скрипт.replace(
        'var $=function(id){return document.getElementById(id)};', заглушка, 1)
    скрипт = скрипт.replace('<script>', '<script>\nwindow.__превью=1;\n', 1)

    out = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Счетикс — блок ' + имя + '</title>'
        + стили +
        '<style>body{margin:0;background:var(--c-bg)}'
        '.превью-шапка{font:600 13px/1.4 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;'
        'color:var(--c-gr);text-align:center;padding:14px 0 0;letter-spacing:.04em}</style>'
        '</head><body><div class="превью-шапка">предпросмотр блока · ' + имя + '</div>'
        '<div id="phr-root"><div class="wp" style="max-width:980px;margin:0 auto;padding:20px 16px">'
        + блок +
        '</div></div>'
        + скрипт +
        '</body></html>'
    )

    цель = os.path.join(ДОМ, '_превью_' + имя + '.html')
    io.open(цель, 'w', encoding='utf-8').write(out)
    print(цель)
    return 0


if __name__ == '__main__':
    sys.exit(главное())
