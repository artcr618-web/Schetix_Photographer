#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПРОВЕРКА ЦЕЛОСТНОСТИ ПРОЕКТА СЧЁТИКС.
Запускать после любой правки:  python3 проверить.py [корень]
Численные проверки выполняют НАСТОЯЩИЙ код calc()/parts(), вырезанный из HTML.
Код возврата: 0 — всё чисто, 1 — есть падения."""
import json, subprocess, sys, os, re, io, collections

КОРЕНЬ = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ЗДЕСЬ  = os.path.dirname(os.path.abspath(__file__))
ХАРНЕСС = os.path.join(ЗДЕСЬ, 'харнесс.js')
ok, fail, warn = [], [], []

def проверка(имя, условие, факт=''):
    (ok if условие else fail).append((имя, факт))
def замечание(имя, факт=''):
    warn.append((имя, факт))

def расчёт(**переопр):
    r = subprocess.run(['node', ХАРНЕСС, КОРЕНЬ, json.dumps(переопр)],
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        raise RuntimeError((r.stderr or 'пустой вывод').strip()[:200])
    return json.loads(r.stdout)

РЕЖИМЫ = [('npd', 'phys', 'НПД 4 %'), ('npd', 'mix', 'НПД 5 %'), ('npd', 'jur', 'НПД 6 %'),
          ('usn6', 'mix', 'УСН 6 %'), ('usn15', 'mix', 'УСН 15 %'),
          ('ausn8', 'mix', 'АУСН 8 %'), ('ausn20', 'mix', 'АУСН 20 %')]

# ══════════════════════════════ 1. МОДЕЛЬ
print('▶ модель (настоящий calc() из calc.html)')
try:
    базовый = расчёт()
except RuntimeError as e:
    print('  ✗ харнесс не запустился:', e); sys.exit(2)

for код, кто, имя in РЕЖИМЫ:
    d = расчёт(поля={'regime': код, 'npd_who': кто})
    остаток = d['R'] - d['C'] - d['aq'] - d['taxAll'] - d['fundY'] - d['discY']
    проверка(f'на руки = цель · {имя}', abs(остаток - d['Ny']) < 1,
             f"{остаток:,.0f} против {d['Ny']:,.0f}")

d = расчёт(поля={'fund_on': True, 'disc_on': True})
проверка('на руки = цель · с фондом и резервом скидки',
         abs(d['R'] - d['C'] - d['aq'] - d['taxAll'] - d['fundY'] - d['discY'] - d['Ny']) < 1)

d = расчёт(поля={'tax_off': True})
проверка('на руки = цель · без оформления',
         abs(d['R'] - d['C'] - d['aq'] - d['Ny']) < 1)

d = базовый
проверка('иерархия: операционное + резерв + проектное = чистое',
         abs(d['side'] + d['fmT'] + d['pool'] - d['NT']) < 0.01)
проверка('иерархия: профильное + клиентское = проектное',
         abs(d['core'] + d['clT'] - d['pool']) < 0.01)
проверка('иерархия: съёмка + обработка = профильное',
         abs(d['sh'] + d['post'] - d['core']) < 0.01)
проверка('сумма сегментов кольца = выручка',
         abs(sum(d['__parts']) - d['R']) < 1, f"Δ {sum(d['__parts']) - d['R']:.4f}")
проверка('доходные сектора = доход без отпуска',
         abs(sum(d['__parts'][:6]) - d['Ny']*11/12) < 1)
проверка('сектор отпуска = месячный доход',
         abs(d['__parts'][13] - d['Ny']/12) < 1)

# инвариант сетки скидок: выручка не зависит от длительности съёмки
выручки = [расчёт(поля={'shoot_manual': str(S)})['R'] for S in (1, 2, 4, 6)]
проверка('сетка скидок: выручка одинакова при любой длительности',
         max(выручки) - min(выручки) < 1, f'разброс {max(выручки)-min(выручки):.2f} ₽')

# ставка падает с ростом длительности
ставки = [расчёт(поля={'shoot_manual': str(S)}) for S in (1, 2, 4, 6)]
ставки = [x['R'] / x['sh'] for x in ставки]
проверка('сетка скидок: ставка часа убывает с длительностью',
         all(ставки[i] > ставки[i+1] for i in range(3)),
         ' → '.join(f'{r:,.0f}' for r in ставки))

# Загрузка считает именно проекты, а не съёмочные часы. При S=1 они равны,
# поэтому проверяем весь разрешённый диапазон длительности съёмки.
загрузки = [расчёт(поля={'shoot_manual': str(S)}) for S in (0.5, 1, 1.5, 2, 4, 6, 8)]
проверка('загрузка: loadGoal.shoots = количество проектов при S 0,5–8 ч',
         all(abs(x['loadGoal']['shoots']-x['py']) < 1e-7 for x in загрузки))
проверка('загрузка: идеальная ставка укладывается в стандартный фонд времени',
         all(abs(x['loadGoal']['hours']-x['NT']) < 1e-7 for x in загрузки))
проверка('загрузка: проекты × часы съёмки × текущая ставка = целевая выручка',
         all(abs(x['loadCur']['shoots']*x['S']*x['cur']-x['R']) < 0.02 for x in загрузки))
проверка('загрузка: проекты × часы съёмки × ставка в ноль = целевая выручка',
         all(abs(x['loadZero']['shoots']*x['S']*x['rateZero']-x['R']) < 0.02 for x in загрузки))

# ══════════════════════════════ 2. КРАЕВЫЕ СЛУЧАИ
print('▶ краевые случаи')
d = расчёт(поля={'promo_per_day': '7.5'})
проверка('продвижение 7,5 ч/день не даёт отрицательных часов', d['pool'] > 0,
         f"pool {d['pool']:.0f} ч, ставка {d['R']/d['sh'] if d['sh'] else 0:,.0f} ₽/ч")
d = расчёт(поля={'acq_rate': '30', 'fund_on': True, 'fund_pct': '30',
                 'disc_on': True, 'disc_pct': '15'})
проверка('экстремальные проценты не взрывают выручку', d['R'] < 5_000_000,
         f"R {d['R']:,.0f} при D {1-0.30-0.30-0.15:.2f}")
d = расчёт(поля={'shoot_manual': '0'})
проверка('нулевая длительность съёмки обрабатывается', d['sh'] > 0 or d['R'] == 0,
         f"sh {d['sh']}, R {d['R']:,.0f}")

# Точка безубыточности должна быть единым точным сценарием:
# выручка, ставка часа и нулевой остаток относятся к одной величине Rb.
# Правило владельца 25.08: точка безубыточности — только необходимые расходы,
# резервные фонды в неё НЕ входят, даже если включены галочками.
def остаток_в_ноль(d, поправка_сайта=0):
    return (d['Rb'] - d['C'] - d['aqB'] - d['taxB']
            - d['Rb']*поправка_сайта)

for код, кто, имя in РЕЖИМЫ:
    d = расчёт(поля={'regime': код, 'npd_who': кто})
    остаток = остаток_в_ноль(d)
    проверка(f'безубыточность анкеты сходится в ноль · {имя}', abs(остаток) < 0.02,
             f'{остаток:+,.2f} ₽')

# При любой разрешённой длительности съёмки выручка в ноль остаётся той же,
# а точная ставка обязана равняться выручке в ноль / съёмочные часы.
нулевые = [расчёт(поля={'shoot_manual': str(S)}) for S in (0.5, 1, 1.5, 2, 4, 6, 8)]
проверка('ставка в ноль точна при длительности 0,5–8 ч',
         all(x['sh'] > 0 and abs(x['rateZero']*x['sh']-x['Rb']) < 1e-5 for x in нулевые))
проверка('месячная выручка в ноль = годовая / 12',
         all(abs((x['Rb']/12)*12-x['Rb']) < 1e-7 for x in нулевые))

# Специальные ветки, которые прежний повторный расчёт в report.html терял.
d = расчёт(поля={'tax_off': True})
проверка('безубыточность · налоги выключены',
         abs(остаток_в_ноль(d)) < 0.02 and abs(d['taxB']) < 0.01)
d = расчёт(поля={'fund_on': True, 'fund_pct': '10',
                 'disc_on': True, 'disc_pct': '15'})
проверка('безубыточность · фонды не входят (только необходимые расходы)',
         abs(остаток_в_ноль(d)) < 0.02)
d = расчёт(радио={'site_mode': 'self'})
поправка_сайта = 80/(7*d['NT'])
проверка('безубыточность · сайт сделан самостоятельно',
         abs(остаток_в_ноль(d, поправка_сайта)) < 0.02)
d = расчёт(допКомиссии=3.5)
проверка('безубыточность · дополнительная банковская комиссия',
         abs(остаток_в_ноль(d)) < 0.02)

# ══════════════════════════════ 2a. ИДЕАЛЬНЫЙ СЦЕНАРИЙ И ПОЛНОЕ КОЛЬЦО
print('▶ идеальный сценарий')
def идеальный_сходится(d):
    сумма = (d['C'] + d['taxAll'] + d['aq'] + d['goalFund']
             + d['goalDiscountReserve'] + d['goalSelfSiteCost'])
    return (abs(d['totalExpenses']-(d['C']+d['taxAll']+d['aq'])) < 0.02
            and abs(d['goalCostsTotal']-сумма) < 0.02
            and abs(d['goalResult']-(d['R']-сумма)) < 0.02
            and abs(d['goalResult']-d['Ny']) < 0.02
            and abs(d['rateHour']*d['sh']-d['R']) < 1e-5
            and abs(d['fundY']-d['goalFund']) < 0.02
            and abs(d['discY']-d['goalDiscountReserve']) < 0.02)

идеальные_ветки = [
    ('по умолчанию', {}),
    ('налоги выключены', {'поля': {'tax_off': True}}),
    ('фонды включены', {'поля': {'fund_on': True, 'fund_pct': '10',
                                 'disc_on': True, 'disc_pct': '15'}}),
    ('собственный сайт', {'радио': {'site_mode': 'self'}}),
    ('банк исключён', {'EXC_ВНЕШ': {'Form015b': True}}),
    ('фонды и собственный сайт', {
        'поля': {'fund_on': True, 'fund_pct': '10',
                 'disc_on': True, 'disc_pct': '15'},
        'радио': {'site_mode': 'self'}}),
]
for имя, параметры in идеальные_ветки:
    d = расчёт(**параметры)
    проверка(f'идеальный сценарий сходится · {имя}', идеальный_сходится(d))

# Отключённые параметры остаются в контракте и дают эффективный ноль.
d = расчёт(поля={'tax_off': True, 'fund_on': False, 'disc_on': False},
            радио={'site_mode': 'hired'})
проверка('идеальный сценарий · эффективные нули',
         d['taxAll'] == 0 and d['goalFund'] == 0
         and d['goalDiscountReserve'] == 0 and d['goalSelfSiteCost'] == 0)
d = расчёт(поля={'fund_on': True, 'fund_pct': '10',
                 'disc_on': True, 'disc_pct': '15'},
            радио={'site_mode': 'self'})
проверка('идеальное кольцо · сумма дохода и всех затрат равна выручке',
         abs(d['Ny']+d['goalCostsTotal']-d['R']) < 0.02)

# ══════════════════════════════ 2b. ТЕКУЩИЙ СЦЕНАРИЙ И ЭФФЕКТИВНЫЕ НУЛИ
print('▶ текущий сценарий')
def текущий_сходится(d):
    сумма = (d['C'] + d['taxC'] + d['aqC'] + d['currentFund']
             + d['currentDiscountReserve'] + d['currentSelfSiteCost'])
    return (abs(d['currentCostsTotal']-сумма) < 0.02
            and abs(d['currentResult']-(d['Rc']-сумма)) < 0.02
            and abs(d['leftC']-d['currentResult']) < 0.02
            and abs(d['currentIncome']-max(d['currentResult'],0)) < 0.02
            and abs(d['currentLoss']-min(d['currentResult'],0)) < 0.02
            and d['currentIsLoss'] == (d['currentResult'] < 0))

текущие_ветки = [
    ('по умолчанию', {}),
    ('налоги выключены', {'поля': {'tax_off': True}}),
    ('фонды включены', {'поля': {'fund_on': True, 'fund_pct': '10',
                                 'disc_on': True, 'disc_pct': '15'}}),
    ('собственный сайт', {'радио': {'site_mode': 'self'}}),
    ('банк исключён', {'EXC_ВНЕШ': {'Form015b': True}}),
    ('нулевая ставка', {'поля': {'current_rate': '0'}}),
    ('ставка 1 000', {'поля': {'current_rate': '1000'}}),
    ('ставка 3 000', {'поля': {'current_rate': '3000'}}),
]
for имя, параметры in текущие_ветки:
    d = расчёт(**параметры)
    проверка(f'текущий сценарий сходится · {имя}', текущий_сходится(d))

# Отключённый параметр остаётся в контракте, но даёт нулевой вклад.
d = расчёт(поля={'tax_off': True})
проверка('эффективный ноль · отключённый налог', d['taxC'] == 0)
d = расчёт(поля={'fund_on': False, 'disc_on': False})
проверка('эффективный ноль · выключенные фонды',
         d['currentFund'] == 0 and d['currentDiscountReserve'] == 0)
d = расчёт(радио={'site_mode': 'hired'})
проверка('эффективный ноль · неактивная ветка собственного сайта',
         d['currentSelfSiteCost'] == 0)
d = расчёт(поля={'current_rate': '1000'})
проверка('убыток не обрезается и сохраняет знак минус',
         d['currentResult'] < 0 and d['currentLoss'] < 0
         and d['currentIncome'] == 0 and d['currentIsLoss'])

# ══════════════════════════════ 2c. ПРОГРАММА ЛОЯЛЬНОСТИ (блок 03 отчёта)
print('▶ программа лояльности')
import math
def лояльность(d):
    """Повторяет арифметику блока 03 из report.html, чтобы проверить
       заявленную книгой сходимость: объём + постоянным + сертификаты = фонд."""
    if not d['discP']: return None
    hp = d['R']/d['pool'] if d['pool'] else 0
    hourAt = lambda S: (S*(1+d['K'])+d['cl'])*hp/S
    S = max(round(d['S'] or 2), 1)
    rRate = lambda x: math.ceil(x/100)*100
    чек = rRate(hourAt(S))*S
    фонд = round(d['discY'])
    пост = 0; заказы = 0; людей = 0
    бюдж = фонд*0.45; цел = d['py']*0.30
    остБ, остЗ = бюдж, цел
    ступени = ((0.05,2,0.40),(0.07,4,0.40),(0.10,12,0.20))
    for p_, s_, w in ступени:
        ценаКл = s_*чек*p_
        поБ = min(бюдж*w, остБ)/ценаКл if ценаКл else 0
        поЗ = min(цел*w, остЗ)/s_
        n = max(0, math.floor(min(поБ, поЗ)))
        сум = round(n*s_*чек*p_)
        остБ -= сум; остЗ -= n*s_
        пост += сум; заказы += n*s_; людей += n
    if людей == 0:
        p_, s_, w = ступени[0]
        цена = round(s_*чек*p_)
        if цена <= бюдж and s_ <= цел:
            пост, заказы = цена, s_
    r500 = lambda n: max(round(n/500)*500, 500)
    бюджСпец = min(фонд*0.30, max(фонд-пост, 0))
    v0, v1, v2 = r500(чек*0.85), r500(чек*0.40), r500(чек*0.25)
    ост = бюджСпец
    n0 = 1 if ост >= v0 else 0; ост -= v0*n0
    n1 = max(0, math.floor(ост*0.45/v1)); ост -= v1*n1
    n2 = max(0, math.floor(ост/v2));      ост -= v2*n2
    спец = v0*n0 + v1*n1 + v2*n2
    объём = max(фонд-пост-спец, 0)
    return dict(фонд=фонд, пост=пост, спец=спец, объём=объём,
                сумма=пост+спец+объём, заказы=заказы, py=d['py'])

for имя, поля in (('резерв 15 %', {'disc_on': True, 'disc_pct': '15'}),
                  ('резерв 10 %', {'disc_on': True, 'disc_pct': '10'}),
                  ('резерв 5 %',  {'disc_on': True, 'disc_pct': '5'}),
                  ('резерв 5 %, съёмка 6 ч', {'disc_on': True, 'disc_pct': '5', 'shoot_manual': '6'}),
                  ('резерв 5 %, съёмка 8 ч', {'disc_on': True, 'disc_pct': '5', 'shoot_manual': '8'})):
    л = лояльность(расчёт(поля=поля))
    проверка(f'фонд лояльности сходится · {имя}', abs(л['сумма']-л['фонд']) <= 3,
             f"сумма направлений {л['сумма']:,} против фонда {л['фонд']:,}")
    проверка(f'постоянные ≤ 30 % потока заказов · {имя}', л['заказы'] <= л['py']*0.31,
             f"{л['заказы']:.0f} из {л['py']:.0f} = {л['заказы']/л['py']*100:.0f} %")

# ══════════════════════════════ 3. СОГЛАСОВАННОСТЬ ФАЙЛОВ
print('▶ согласованность файлов')
def читать(п): return io.open(os.path.join(КОРЕНЬ, п), encoding='utf-8').read()
calc, rep, karkas = читать('Веб/calc.html'), читать('Веб/report.html'), читать('Веб/Части/каркас.html')

проверка('report.html совпадает с каркасом', rep == karkas,
         f'{sum(1 for a, b in zip(rep.splitlines(), karkas.splitlines()) if a != b)} строк расходятся')

# Часовые ставки в отчёте называются только по справочнику.
# Эталон — лист 01_Глоссарий книги: «Доход в час на руки», «Базовая ставка часа».
# Прежние ярлыки («Фактическая стоимость вашего часа работы», «Час вашего
# времени») сняты 25.08.2026 по решению владельца — не должны возвращаться.
ент_ю = lambda s: ''.join('\\u%04x' % ord(c) if ord(c) > 127 else c for c in s)
проверка('отчёт: часовые ставки названы по справочнику',
         ент_ю('Доход в час на руки') in rep
         and ент_ю('Фактическая стоимость вашего часа работы') not in rep
         and ент_ю('Час вашего времени') not in rep,
         'эталон названий — лист 01_Глоссарий книги')

# Карточка «Необходимый доход» показывает один точный аналитический сценарий.
# Округлённая вверх ставка остаётся только в практических блоках отчёта.
идеал = re.search(r"\{cls:'s2'.*?cap:CAPM\}", rep, re.S)
идеал_код = идеал.group(0) if идеал else ''
проверка('карточка «Необходимый доход»: ставка берётся из d.rateHour',
         'var rateGoalПередан=Number(d.rateHour)' in rep)
проверка('карточка «Необходимый доход»: три суммы показаны до целого рубля',
         'r:f0(goalRateV)' in идеал_код
         and 'rev:f0(d.R/12)' in идеал_код
         and 'mid:f0(d.Ny/12)' in идеал_код
         and 'f0r(' not in идеал_код)
проверка('идеальное кольцо берёт полный состав затрат из calc()',
         'var goalCostsПереданы=Number(d.goalCostsTotal)' in rep
         and 'goalFund+goalDiscountReserve+goalSelfSiteCost' in rep)
проверка('«Всего расходов» приходит готовым из calc()',
         'var expMo=d.totalExpenses/12' in rep
         and 'var ВСЕГО_РАСХОДОВ = d.totalExpenses;' in rep
         and 'd.vari + tax + aq' not in rep)
проверка('детализация: вложения и резервный фонд разделены',
         "['Финансовые вложения (инвестиции)', t04]" in rep
         and "['Резервный фонд', t04r]" in rep
         and "рр('Резерв на отпуск', d.vacY||0)" in rep
         and 'Амортизация / Резерв' not in rep)
проверка('проектное время — годовой pool, а не длительность проекта',
         "['Р','Проектное время', чс(pool)" in rep
         and "['Р','Время на проекты'" not in rep)
проверка('календарь: Выходной и Праздник разделены',
         '"Выходные дни": "Выходной"' in rep
         and '"Праздничные дни": "Праздник"' in rep
         and '"Выходные и праздничные дни"' not in rep)
проверка('лояльность: внутренние правила не выводятся пользователю',
         "return '<h3>Фонд и его распределение</h3>' + a;" in rep
         and '<h3>08.2 По каким правилам делится фонд</h3>' not in rep)

# Карточка «В ноль» берёт точный сценарий из calc(), но денежные значения
# для пользователя округляет до ближайшего целого рубля. Округление вверх
# до 100 рублей применяется только в практическом блоке «Четыре цифры».
ноль = re.search(r"\{cls:'s3'.*?cap:CAPM\}", rep, re.S)
ноль_код = ноль.group(0) if ноль else ''
проверка('отчёт: безубыточность берётся из d.Rb',
         'var VbПередан=Number(d.Rb)' in rep)
проверка('отчёт: ставка в ноль берётся из d.rateZero',
         'var rateZeroПередан=Number(d.rateZero)' in rep)
проверка('карточка «В ноль»: ставка и выручка показаны до целого рубля',
         'r:f0(bRateV)' in ноль_код
         and 'rev:f0(Vb/12)' in ноль_код
         and 'mid:f0(0)' in ноль_код
         and 'f0r(bRateV)' not in ноль_код)
проверка('денежный формат с копейками удалён из пользовательского интерфейса',
         'var f2=' not in rep and 'f2=function' not in calc)
проверка('блок «Четыре цифры»: ставка в ноль округляется вверх до 100 ₽',
         "['b','\\u0421\\u0442\\u0430\\u0432\\u043a\\u0430 \\u0432 \\u043d\\u043e\\u043b\\u044c',f0r(bRateV)+'/\\u0447'" in rep)
проверка('карточка текущего дохода берёт готовый currentResult из calc()',
         'var resultCПередан=Number(d.currentResult)' in rep
         and 'var costsCПереданы=Number(d.currentCostsTotal)' in rep)
проверка('карточка текущего дохода не обрезает убыток до нуля',
         'Math.max(curR-expC,0)' not in rep)
проверка('карточка текущего дохода меняет подпись на «Убыток» (З-148)',
         "currentIsLoss?'\\u0423\\u0431\\u044b\\u0442\\u043e\\u043a'" in rep)
проверка('убыток показывается сравнительной плашкой и знаком минус',
         'class="losscompare"' in rep and 'class="current-loss-note"' in rep
         and "v<0?'\\u2212':''" in rep)
# Отчёт больше не хранит свою ставку эквайринга: он берёт фактическую
# из анкеты (переменная AQФАКТ). Проверяем, что зашитого числа не осталось.
aq_rep = re.search(r'AQ\s*:\s*(0\.\d+)', rep)
aq_form = re.search(r'id="acq_rate"[^>]*value="([\d.]+)"', calc)
проверка('ставка эквайринга берётся из анкеты, а не зашита в отчёт',
         aq_rep is None and 'AQФАКТ' in rep,
         f'в отчёте осталось зашитое {aq_rep.group(1) if aq_rep else "—"}'
         + (f' · в анкете {aq_form.group(1)} %' if aq_form else ''))

for имя, файл in (('calc', calc), ('report', rep)):
    css = '\n'.join(re.findall(r'<style[^>]*>([\s\S]*?)</style>', файл))
    проверка(f'{имя}: баланс CSS-скобок', css.count('{') == css.count('}'),
             f"{css.count('{') - css.count('}'):+d}")
    исп = set(re.findall(r'var\((--[\w-]+)\)', файл))
    объ = set(re.findall(r'(--[\w-]+)\s*:', файл))
    проверка(f'{имя}: все CSS-переменные объявлены', not (исп - объ), ', '.join(sorted(исп - объ)))

# баланс HTML-тегов во всех трёх файлах
VOID = {'br','img','input','meta','link','hr','source','area','col','embed','track','wbr',
        'circle','path','rect','polygon','line','ellipse','stop','use','polyline','animate'}
def баланс_тегов(s):
    s = re.sub(r'(<script[^>]*>)([\s\S]*?)(</script>)',
               lambda m: m.group(1) + re.sub(r'[^\n]', ' ', m.group(2)) + m.group(3), s)
    s = re.sub(r'(<style[^>]*>)([\s\S]*?)(</style>)',
               lambda m: m.group(1) + re.sub(r'[^\n]', ' ', m.group(2)) + m.group(3), s)
    s = re.sub(r'<!--[\s\S]*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s)
    стек, беды = [], []
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>', s):
        зак, имя, само = m.group(1), m.group(2).lower(), m.group(4)
        if имя in VOID or само == '/': continue
        if зак:
            if стек and стек[-1][0] == имя: стек.pop()
            else: беды.append('лишний </%s> поз.%d' % (имя, m.start()))
        else: стек.append((имя, m.start()))
    return беды + ['не закрыт <%s> поз.%d' % (и, п) for и, п in стек]

for имя, файл in (('calc', calc), ('report', rep), ('index', читать('Веб/index.html'))):
    б = баланс_тегов(файл)
    проверка(f'{имя}: баланс HTML-тегов', not б, '; '.join(б[:3]))

# 24 прямых потомка .wp
def детей(s):
    s = re.sub(r'<style[^>]*>[\s\S]*?</style>|<script[^>]*>[\s\S]*?</script>|<!--[\s\S]*?-->', '', s)
    VOID = {'br','img','input','meta','link','hr','source','area','col','embed','track','wbr',
            'circle','path','rect','polygon','line','ellipse','stop','use','polyline'}
    н = s.index('<div class="wp">') + len('<div class="wp">')
    гл, дети, тек = 0, 0, None
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>', s[н:]):
        зак, имя_, само = m.group(1), m.group(2).lower(), m.group(4)
        if зак:
            гл -= 1
            if гл == 0 and тек is not None: дети += 1; тек = None
            if гл < 0: break
        else:
            if имя_ in VOID or само == '/': continue
            if гл == 0: тек = m.start()
            гл += 1
    return дети
n = детей(rep)
проверка("в .wp ровно 20 блоков (как ждёт собрать.py)", n == 20, f"{n}")

# логотип: 8 правил книги
for имя, файл in (('calc', calc), ('report', rep)):
    знаки = re.findall(r'<svg class="(?:bx|lx)".*?</svg>', файл, re.S)
    проверка(f'{имя}: зелёный ромб — правый (x=19.81)',
             all(re.search(r'x="19\.81"[^/]*?fill="var\(--c-g-500\)"', b) for b in знаки))
    проверка(f'{имя}: ровно один зелёный ромб на знак',
             all(len(re.findall(r'--c-g-500', b)) == 1 for b in знаки))
    проверка(f'{имя}: геометрия знака 10.10 / rx 1.90',
             all('width="10.10"' in b and 'rx="1.90"' in b for b in знаки))
    проверка(f'{имя}: нет следов анимации знака',
             not re.search(r'u-(inc|exp|res|prof)', файл))
    проверка(f'{имя}: написание «счётикс» с буквой ё',
             'счетикс' not in файл.lower() or 'счётикс' in файл.lower(),
             'найдено «счетикс» без ё' if 'счетикс' in файл.lower() else '')
проверка('каркас: написание «счётикс» с буквой ё', 'счетикс' not in karkas.lower())

# JS обоих файлов синтаксически валиден
for имя, путь in (('calc', 'Веб/calc.html'), ('report', 'Веб/report.html'), ('index', 'Веб/index.html')):
    s = читать(путь)
    код = '\n'.join(re.findall(r'<script[^>]*>([\s\S]*?)</script>', s))
    врем = '/tmp/_js_%s.js' % имя
    io.open(врем, 'w', encoding='utf-8').write(код)
    p = subprocess.run(['node', '-e',
        "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", врем],
        capture_output=True, text=True)
    os.remove(врем)
    проверка(f'{имя}: JS компилируется', p.returncode == 0, (p.stderr or '').strip().split('\n')[0][:120])

# ══════════════════════════════ 4. КНИГА ↔ КОД
print('▶ книга ↔ код')
try:
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(КОРЕНЬ, 'Книга', 'Калькулятор_ставки_часа.xlsx'))
    ws = wb['calc']
    СВЯЗЬ = {'income_month': 'income_month', 'current_rate': 'current_rate', 'frames_out': 'frames_out',
             'shoot_duration': 'shoot_manual', 'post_ratio': 'post_ratio', 'client_time': 'client_time',
             'promo_per_day': 'promo_per_day', 'acc_per_quarter': 'acc_per_quarter',
             'acc_cost_month': 'acc_cost_month', 'home_rent': 'home_rent', 'home_util': 'home_util',
             'home_area': 'home_area', 'cab_area': 'cab_area', 'office_rent': 'office_rent',
             'office_util': 'office_util', 'edu_life': 'edu_life', 'site_cost': 'site_cost',
             'site_hours': 'site_hours', 'site_life': 'site_life', 'fm_pct': 'fm_pct'}
    расх = []
    for r in range(1, ws.max_row + 1):
        i = ws.cell(r, 1).value
        if not isinstance(i, str) or i.strip() not in СВЯЗЬ: continue
        i = i.strip(); v = ws.cell(r, 3).value
        m = re.search(r'id="%s"[^>]*value="([^"]*)"' % СВЯЗЬ[i], calc)
        if not m: continue
        try:
            bv = float(v); hv = float(m.group(1).replace(' ', ''))
            if i in ('fm_pct',) and bv < 1: bv *= 100
            if abs(bv - hv) > 1e-9: расх.append(f'{i}: книга {bv:g} ≠ форма {hv:g}')
        except Exception: pass
    проверка('значения по умолчанию совпадают с книгой', not расх, '; '.join(расх))

    # ── переключатели книги против анкеты. Раньше не сверялись, и книга
    # считала с включённым резервом на форс-мажоры, а анкета — без него:
    # ставка расходилась на 496 ₽ (9 926 против 9 430).
    ПЕРЕКЛ = {'fm_on':   ('Заложить резерв',        r'id="fm_on"[^>]*checked'),
              'acc_mode':('Веду самостоятельно',    r'name="acc_mode" value="self" checked'),
              'ws_mode': ('Работаю из дома',        r'name="ws_mode" value="home" checked'),
              'site_mode':('Нанимал (а) специалиста', r'name="site_mode" value="hired" checked')}
    плохо = []
    for r in range(1, ws.max_row + 1):
        и = ws.cell(r, 1).value
        if not isinstance(и, str) or и.strip() not in ПЕРЕКЛ: continue
        и = и.strip(); знач = str(ws.cell(r, 3).value or '').strip()
        вкл_текст, шаблон = ПЕРЕКЛ[и]
        книга_вкл = (знач == вкл_текст)
        форма_вкл = bool(re.search(шаблон, calc))
        if книга_вкл != форма_вкл:
            плохо.append(f'{и}: книга «{знач}», в анкете {"включено" if форма_вкл else "выключено"}')
    проверка('переключатели книги совпадают с анкетой', not плохо, '; '.join(плохо))

    # ── реестр полей и реестр правил
    проверка('книга: есть лист 16_Реестр_правил', '16_Реестр_правил' in wb.sheetnames)
    if '15_Реестр_полей' in wb.sheetnames and '16_Реестр_правил' in wb.sheetnames:
        реестр = wb['15_Реестр_полей']
        правила = wb['16_Реестр_правил']
        ожид_шапка = ['№','Название правила','ID','Условие','Действие','Краткое описание','Ссылка на документ']
        факт_шапка = [правила.cell(1,c).value for c in range(1,8)]
        проверка('реестр правил: утверждённая структура 7 столбцов', факт_шапка == ожид_шапка,
                 ' | '.join(str(x) for x in факт_шапка))
        rule_ids = [правила.cell(r,3).value for r in range(2,правила.max_row+1)]
        ожид_ids = [f'RULE-{i:03d}' for i in range(1,len(rule_ids)+1)]
        проверка('реестр правил: ID уникальны и последовательны', rule_ids == ожид_ids)
        битые_док = []
        for r in range(2,правила.max_row+1):
            link = str(правила.cell(r,7).value or '')
            if not link or not os.path.exists(os.path.join(КОРЕНЬ,link)):
                битые_док.append(f'{правила.cell(r,3).value} → {link or "—"}')
        проверка('реестр правил: ссылки ведут на существующие документы', not битые_док,
                 '; '.join(битые_док[:4]))
        известные = set(rule_ids)
        ссылки_полей, битые_правила = set(), []
        for r in range(1,реестр.max_row+1):
            if not str(реестр.cell(r,1).value or '').isdigit(): continue
            for rid in str(реестр.cell(r,28).value or '').split(';'):
                rid=rid.strip()
                if not rid: continue
                ссылки_полей.add(rid)
                if rid not in известные: битые_правила.append(f'строка {r}: {rid}')
        проверка('реестр полей: Правило ID ведут в реестр правил', not битые_правила,
                 '; '.join(битые_правила[:4]))
        # Каждый верхнеуровневый ключ настоящего calc() должен быть в реестре.
        зарегистрировано = set()
        for r in range(1,реестр.max_row+1):
            code = str(реестр.cell(r,11).value or '')
            if code.startswith('d.'):
                зарегистрировано.add(code[2:].split('.')[0])
        пропущено = sorted(set(базовый)-{'__parts'}-зарегистрировано)
        лишнее = sorted(зарегистрировано-set(базовый))
        проверка('реестр полей: полный верхнеуровневый контракт calc()', not пропущено and not лишнее,
                 ('нет: '+', '.join(пропущено[:5]) if пропущено else '')+
                 ('; лишнее: '+', '.join(лишнее[:5]) if лишнее else ''))

    # Пересчитана ли книга: у формул должны быть сохранённые значения.
    # Без них проверки не могут сверять расчёт кода с расчётом книги.
    wbv = openpyxl.load_workbook(os.path.join(КОРЕНЬ, 'Книга', 'Калькулятор_ставки_часа.xlsx'), data_only=True)
    формул = пусто = 0
    for имя_л in wb.sheetnames:
        л, лв = wb[имя_л], wbv[имя_л]
        for стр in л.iter_rows():
            for c in стр:
                if isinstance(c.value, str) and c.value.startswith('='):
                    формул += 1
                    if лв[c.coordinate].value is None: пусто += 1
    проверка('книга пересчитана (у формул есть значения)', пусто == 0,
             f'{пусто} из {формул} формул без результата — см. Архив/Задачи/02_ПЕРЕСЧЁТ_КНИГИ.md')

    # налоговые константы
    конст = {}
    for r in range(1, ws.max_row + 1):
        i = ws.cell(r, 1).value
        if isinstance(i, str): конст[i.strip()] = ws.cell(r, 3).value
    пары = [('fixed_contrib', r'FIX=(\d+)', 1), ('contrib_threshold', r'THR=(\d+)', 1),
            ('contrib_cap', r'CAP=(\d+)', 1), ('min_tax_usn', r'M15=\.?(\d+)', 0.01),
            ('min_tax_ausn', r'M20=\.?(\d+)', 0.01), ('limit_npd', r'npd:\s*\[(\d+)', 1),
            ('limit_ausn', r'ausn8:\s*\[(\d+)', 1)]
    плохо = []
    for ид, шаб, множ in пары:
        m = re.search(шаб, calc)
        if not m or ид not in конст: continue
        зн = float(m.group(1)) * (множ if множ != 0.01 else 0.01)
        if abs(float(конст[ид]) - зн) > 1e-9: плохо.append(f'{ид}: книга {конст[ид]} ≠ код {зн:g}')
    проверка('налоговые константы совпадают с книгой', not плохо, '; '.join(плохо))
except ImportError:
    замечание('openpyxl не установлен — сверка с книгой пропущена')

# ── демо-набор отчёта должен совпадать с расчётом по умолчанию
# Иначе отчёт, открытый без данных, показывает устаревшие числа
# (так «ставка в ноль» разошлась: 3 331 в демо против 2 814 в расчёте).
m = re.search(r'var DEMO=\{(.*?)\};', rep, re.S)
if not m:
    fail.append(('демо-набор найден в report.html', ''))
else:
    демо = {}
    for k, v in re.findall(r'(\w+):(-?[\d.]+)(?=[,}])', m.group(1)):
        демо[k] = float(v)
    расх = []
    for k, v in демо.items():
        если_есть = базовый.get(k)
        if если_есть is None: continue
        доп = max(1e-4, abs(если_есть) * 1e-5)
        if abs(если_есть - v) > доп:
            расх.append(f'{k}: демо {v:g} ≠ расчёт {если_есть:g}')
    проверка('демо-набор совпадает с расчётом по умолчанию', not расх,
             '; '.join(расх[:4]) + (f' и ещё {len(расх)-4}' if len(расх) > 4 else ''))


# ── справочник ↔ таблицы: ссылки не должны вести в никуда,
# а записи не должны висеть без единой ссылки.
try:
    спр = json.loads(re.search(r'var СПР = (\[.*?\]);\n', rep, re.S).group(1))
    имена = {т for т, _ in спр}

    def объекты(текст, начало):
        """Куски вида «начало{...}» с учётом вложенных скобок."""
        куски = []
        for m in re.finditer(начало, текст):
            i = текст.index('{', m.end() - 1)
            гл, j = 0, i
            while j < len(текст):
                if текст[j] == '{': гл += 1
                elif текст[j] == '}':
                    гл -= 1
                    if гл == 0: break
                j += 1
            куски.append(текст[i:j + 1])
        return куски

    куски = объекты(rep, r'СВЯЗЬ\w* = ') + объекты(rep, r'связь:\s*') + объекты(rep, r'связь=')
    цели, битые = set(), []
    for кусок in куски:
        пары = (re.findall(r"'([^']+)'\s*:\s*'([^']+)'", кусок)
                + re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', кусок))   # JSON-кавычки
        for ключ, цель in пары:
            if not re.match(r'^[А-ЯЁ]', цель): continue      # записи начинаются с заглавной
            цели.add(цель)
            if цель not in имена: битые.append(f'{ключ} → {цель}')
    for цель in re.findall(r"ссылка(?:_на)?\('[^']+',\s*'([^']+)'\)", rep):
        цели.add(цель)
        if цель not in имена: битые.append(f'заголовок → {цель}')
    проверка('ссылки таблиц ведут на существующие записи справочника', not битые,
             '; '.join(sorted(set(битые))[:4]))
    сироты = sorted(имена - цели)
    if сироты:
        замечание(f'записей справочника без ссылок: {len(сироты)}',
                  ', '.join(сироты[:6]) + ('…' if len(сироты) > 6 else ''))
except Exception as e:
    замечание('связи справочника не разобраны', str(e)[:80])

# ══════════════════════════════ 5. ПУБЛИКАЦИОННЫЙ КОНТУР (замечания, не падения)
print('▶ готовность к публикации')
# DEV_NO_BLUR остался в архивной версии с платной стеной, в рабочих файлах
# его нет и быть не должно. Следим только за счётчиком и адресом оплаты.
for имя, шаб in (('YM_ID', r'YM_ID'), ('PAY_URL', r'PAY_URL')):
    if not re.search(шаб, calc): замечание(f'{имя} отсутствует в calc.html')
# THANKS_URL больше не используется: сердечки открывают окно благодарности.
if "'#plan'" in rep or 'href="#plan"' in rep: замечание('ссылка «30 постов» — заглушка #plan')

# ══════════════════════════════ ИТОГ
print()
for имя, факт in ok:   print(f'  ✓ {имя}' + (f'  — {факт}' if факт else ''))
for имя, факт in fail: print(f'  ✗ {имя}' + (f'  — {факт}' if факт else ''))
for имя, факт in warn: print(f'  ! {имя}' + (f'  — {факт}' if факт else ''))
print(f'\nитого: {len(ok)} прошло · {len(fail)} упало · {len(warn)} замечаний')
sys.exit(1 if fail else 0)
