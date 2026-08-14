# -*- coding: utf-8 -*-
"""Сторож логотипа: сверяет знак в HTML с эталоном из книги (лист 09d_Логотип).
   Запуск:  python3 проверка_логотипа.py
   Печатает ОК или список расхождений."""
import re, sys

FILES = ['/home/user/web/report.html', '/home/user/web/calc.html']
RULES = [
    ('зелёный ромб — правый (x=19.81)',
     lambda s: all(re.search(r'x="19\.81"[^/]*?fill="var\(--c-g-500\)"', b) for b in blocks(s)),),
    ('ровно один зелёный на знак',
     lambda s: all(len(re.findall(r'--c-g-500', b)) == 1 for b in blocks(s)),),
    ('три серых ромба (--c-ln на белом, --c-gr3 на сером фоне)',
     lambda s: all(b.count('--c-ln)') == 3 or b.count('--c-gr3)') == 3
                   for b in blocks(s)),),
    ('надпись слева, знак справа',
     lambda s: not re.search(r'<div class="brand"[^>]*><svg', s),),
    ('нет следов анимации (u-inc/u-exp/...)',
     lambda s: not re.search(r'u-(inc|exp|res|prof)', s),),
    ('нет CSS-правил подсветки',
     lambda s: not re.search(r'\.(bx|lx) \.u', s),),
    ('геометрия: сторона 10.10',
     lambda s: all('width="10.10"' in b for b in blocks(s)),),
    ('скругление rx=1.90',
     lambda s: all('rx="1.90"' in b for b in blocks(s)),),
]

def blocks(s):
    return re.findall(r'<svg class="(?:bx|lx)".*?</svg>', s, re.S)

bad = 0
for f in FILES:
    s = open(f, encoding='utf-8').read()
    n = len(blocks(s))
    print('%s — знаков: %d' % (f.split('/')[-1], n))
    for name, test in RULES:
        try:
            ok = test(s)
        except Exception as e:
            ok = False
        if not ok:
            print('   ОШИБКА: ' + name); bad += 1
print()
print('ЛОГОТИП В ПОРЯДКЕ' if not bad else 'НАЙДЕНО РАСХОЖДЕНИЙ: %d' % bad)
sys.exit(1 if bad else 0)
