#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Добавляет невидимые стабильные технические ID страниц и смысловых блоков.

ID не зависят от пользовательской нумерации и не меняют внешний вид. Повторный
запуск безопасен: уже размеченный блок пропускается.
"""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]


def inject(text, pattern, block_id, name='', flags=0):
    # Если этот ID уже присутствует, повторно ничего не добавляем.
    if f'data-block-id="{block_id}"' in text:
        return text, 0
    m = re.search(pattern, text, flags)
    if not m:
        raise RuntimeError(f'Не найден блок {block_id}: {pattern}')
    tag = m.group(0)
    if 'data-block-id=' in tag:
        raise RuntimeError(f'У найденного тега уже другой block-id: {tag}')
    attrs = f' data-block-id="{block_id}"'
    if name:
        attrs += f' data-block-name="{html.escape(name, quote=True)}"'
    new_tag = tag[:-1] + attrs + '>'
    return text[:m.start()] + new_tag + text[m.end():], 1


def page_id(text, root_id, value):
    if f'data-page-id="{value}"' in text:
        return text
    pat = rf'<div\b[^>]*\bid="{re.escape(root_id)}"[^>]*>'
    m = re.search(pat, text)
    if not m:
        raise RuntimeError(f'Не найден корень {root_id}')
    tag = m.group(0)
    return text[:m.start()] + tag[:-1] + f' data-page-id="{value}">' + text[m.end():]


def class_pattern(tag, exact_class):
    return rf'<{tag}\b[^>]*\bclass="{re.escape(exact_class)}"[^>]*>'


def id_pattern(tag, dom_id):
    return rf'<{tag}\b[^>]*\bid="{re.escape(dom_id)}"[^>]*>'


# ---------- calc.html ----------
p = ROOT / 'Веб' / 'calc.html'
t = page_id(p.read_text(encoding='utf-8'), 'phc-root', 'PAGE-CALC')
calc = [
    (class_pattern('div','tbar'), 'CALC-B001', 'Верхняя панель'),
    (id_pattern('div','trustBar'), 'CALC-B002', 'Плавающая панель'),
    (class_pattern('div','hdr'), 'CALC-B003', 'Шапка анкеты'),
    (class_pattern('div','hero-cover'), 'CALC-B004', 'Вводный баннер'),
    (class_pattern('section','benefits'), 'CALC-B005', 'Преимущества'),
    (r'<div\b[^>]*\bclass="core-inputs"[^>]*>', 'CALC-B006', 'Основные данные'),
]
# Все 20 пользовательских карточек получают отдельный технический ID.
for n in range(1, 21):
    bid = f'CALC-B{n+6:03d}'
    pat = rf'<div\b[^>]*\bclass="card(?: [^"]*)?"[^>]*(?=><div class="bn">{n:02d}</div>)'
    # В паттерне намеренно нет закрывающего >: добавляем его временно для общей функции.
    m = re.search(pat, t)
    if f'data-block-id="{bid}"' not in t:
        if not m:
            raise RuntimeError(f'Не найдена карточка {n:02d}')
        tag = m.group(0)
        name = f'Вопрос {n:02d}'
        t = t[:m.start()] + tag + f' data-block-id="{bid}" data-block-name="{name}"' + t[m.end():]

calc += [
    (class_pattern('div','sect'), 'CALC-B027', 'Как мы считаем'),
    (class_pattern('div','cnd'), 'CALC-B028', 'Условия труда по ТК РФ'),
    (class_pattern('div','workmore-note'), 'CALC-B029', 'Можно ли работать больше'),
    (class_pattern('div','form-section form-section-time'), 'CALC-B030', 'Съёмка и обработка'),
    (class_pattern('div','form-section form-section-expenses'), 'CALC-B031', 'Расходы'),
    (class_pattern('div','form-section form-section-reserves'), 'CALC-B032', 'Резервы'),
    (class_pattern('div','savebar'), 'CALC-B033', 'Действия анкеты'),
    (id_pattern('div','trial'), 'CALC-B034', 'Пробный режим'),
    (class_pattern('div','foot'), 'CALC-B035', 'Подвал'),
    (id_pattern('div','ld'), 'CALC-B036', 'Анимация расчёта'),
    (id_pattern('div','limBar'), 'CALC-B037', 'Уведомление о лимите'),
    (id_pattern('div','shModal'), 'CALC-B038', 'Поделиться'),
    (id_pattern('div','thxModal'), 'CALC-B039', 'Благодарность'),
]
for pat,bid,name in calc:
    t,_ = inject(t,pat,bid,name)

# Взаимоисключающие и условные части блоков получают отдельные ID веток.
branches = [
    ('npdWho', 'CALC-B008-S01', 'Заказчики НПД'),
    ('ws_home', 'CALC-B018-S01', 'Рабочее место дома'),
    ('ws_off', 'CALC-B018-S02', 'Отдельное помещение'),
    ('site_c_w', 'CALC-B020-S01', 'Сайт заказан'),
    ('site_h_w', 'CALC-B020-S02', 'Сайт создан самостоятельно'),
    ('acc_h_w', 'CALC-B023-S01', 'Учёт самостоятельно'),
    ('acc_c_w', 'CALC-B023-S02', 'Учёт ведёт специалист'),
    ('bank_acq_group', 'CALC-B022-S01', 'Эквайринг'),
    ('bank_share_row', 'CALC-B022-S02', 'Доля безналичных платежей'),
    ('disc_lvls', 'CALC-B026-S01', 'Уровни программы лояльности'),
]
for dom_id, branch_id, branch_name in branches:
    if f'data-branch-id="{branch_id}"' in t:
        continue
    pat = rf'<[A-Za-z][A-Za-z0-9]*\b[^>]*\bid="{re.escape(dom_id)}"[^>]*>'
    m = re.search(pat, t)
    if not m:
        raise RuntimeError(f'Не найдена ветка {dom_id}')
    tag = m.group(0)
    attrs = (f' data-branch-id="{branch_id}" '
             f'data-branch-name="{html.escape(branch_name, quote=True)}"')
    t = t[:m.start()] + tag[:-1] + attrs + '>' + t[m.end():]
p.write_text(t,encoding='utf-8')

# ---------- report.html и каркас ----------
report_blocks = [
    (id_pattern('div','topbar'), 'REPORT-B001', 'Верхняя панель'),
    (class_pattern('div','hdr'), 'REPORT-B002', 'Шапка отчёта'),
    (class_pattern('div','hwrap'), 'REPORT-B003', 'Главный экран'),
    (class_pattern('div','savebar top'), 'REPORT-B004', 'Поблагодарить проект — верх'),
    (class_pattern('div','wnote'), 'REPORT-B005', 'Из чего складывается цена'),
    (class_pattern('div','logi'), 'REPORT-B006', 'Логистика'),
    (id_pattern('div','card01'), 'REPORT-B007', 'Как распределяется бюджет'),
    (id_pattern('div','card02'), 'REPORT-B008', 'Как распределяется время'),
    (id_pattern('div','card06'), 'REPORT-B009', 'Скидка'),
    (class_pattern('div','thxbar'), 'REPORT-B010', 'Поблагодарить проект — середина'),
    (id_pattern('div','card07'), 'REPORT-B011', 'Налоговый режим'),
    (id_pattern('div','card04'), 'REPORT-B012', 'Три сценария работы'),
    (id_pattern('div','card05'), 'REPORT-B013', 'Больше заказов'),
    (id_pattern('div','card09'), 'REPORT-B014', 'Четыре цифры'),
    (id_pattern('div','card10'), 'REPORT-B015', 'Объяснение стоимости клиенту'),
    (class_pattern('div','logi logiw'), 'REPORT-B016', 'Итоговое уведомление'),
    (class_pattern('div','cta thx'), 'REPORT-B017', 'Финальная благодарность'),
    (id_pattern('div','спрдет'), 'REPORT-B018', 'Справочник и детализация'),
    (id_pattern('div','trial'), 'REPORT-B019', 'Пробный режим'),
    (class_pattern('div','foot'), 'REPORT-B020', 'Подвал'),
]
for rel in ['Веб/report.html','Веб/Части/каркас.html']:
    p = ROOT / rel
    t = page_id(p.read_text(encoding='utf-8'), 'phr-root', 'PAGE-REPORT')
    for pat,bid,name in report_blocks:
        t,_ = inject(t,pat,bid,name)
    p.write_text(t,encoding='utf-8')

# ---------- index.html ----------
p = ROOT / 'Веб' / 'index.html'
t = page_id(p.read_text(encoding='utf-8'), 'phw-root', 'PAGE-INDEX')
for pat,bid,name in [
    (class_pattern('div','in'), 'INDEX-B001', 'Главный экран обложки'),
    (class_pattern('div','foot'), 'INDEX-B002', 'Подвал'),
]:
    t,_ = inject(t,pat,bid,name)
p.write_text(t,encoding='utf-8')

print('Размечено: PAGE-INDEX 2 блока · PAGE-CALC 39 блоков · PAGE-REPORT 20 блоков')
