# Дорожная карта сведения calc.html ↔ report.html — 25.09.2026
# Канон: 97bc09f, FormMgmt checked (управление выключено по умолчанию), Form024 checked (сотрудники выключены), fund_on/cushion_on без checked

## Цель
Посчитать, все ли функции учтены, все ли значения считаются. Показать расхождения DEMO vs живой дефолт, дефекты кольца/легенды/таблиц/роста, мёртвые блоки, инварианты. Старая карта Н-01…Н-09 остаётся — проходим после сведения.

## Фаза 1 · Инвентарь calc.html

### 1.1 Формы (24 ключа CAT + 3 времени)
- Время: FormClientTime (вопрос 07), FormPromoTime (08), FormMgmt (09) — в pool, side, gross, NT→pool. FormMgmt checked по умолчанию → mgmtT=0 в дефолте.
- Техника: Form001 (камера, вопрос 10), Form001b (доп. оборудование), Form002 (офис, 11)
- Софт/подписки: Form003 (per, 12), Form004 (life, плагины)
- Место: Form009b (13, режим home/office), Form013 (life, обустройство), Form013b (ремонт)
- Обучение: Form006 (months, 14) — eduSum, eduMon, eduOpp=eduMon*income_month, eduY=(eduSum+eduOpp)/eduL, depEdu=0 по слову 15.09
- Сайт: Form010 (per, реклама, 16, включает site_cost/site_life/site_hours/site_mode), Form014 (старый ключ, сейчас EXC Form014||Form010) — siteY, sdiv
- Деньги: Form007 (per, банк), Form012 (per, кредит), Form015b (bank_extra, доп комиссии), Form011 (бухучёт, acc_mode self/наём), Form024 (наёмные, 18, per, checked по умолчанию)
- Резервы: Form018 fm_on/fm_pct (19, резерв времени), Form017 disc_on/disc_pct (20, скидка), Form016 fund_on/fund_pct (22, прибыль), Form019 cushion_on/cushion_pct (21, буфер)
- EXC: Form001, Form001b, Form002, Form003, Form004, Form006, Form007, Form008b (подписки+софт группа), Form009b (место), Form010, Form011, Form012, Form013, Form013b, Form015b, Form024, FormMgmt — всего 16 чекбоксов исключения.

### 1.2 Что возвращает calc() — 103+ поля в d
- Ответы: answers[], catalog[] (позиции)
- Календарь: NT, WD, VAC, SICK, ND, EFF, idle, CAL=365, WEEKEND=104, HOLI=14
- Камера: shPerHour, shLife, shotsYear, camName, camPrice, camLife, camAmort (Σ по всем строкам Form001), camWear
- Время: promo, accT, fmT, mgmtT, pool, S, pt, py, sh, post, clT, gross, side, ПРЕДЕЛ_СТОРОННЕГО
- Деньги: amort, vari, C, Ny, vacY, wsY, siteY, eduY, totalExpenses, R, taxAll, aq, Rb, taxB, aqB
- Резервы: fundY=goalFund, discY, fundP, discP, cushionShare, profitP=fundP+cushionShare, fundY=R*profitP, goalFund, goalDiscountReserve, goalSelfSiteCost, goalCostsTotal, goalResult
- Текущая ставка: cur, Rc, leftC, taxC, aqC, currentFund, currentDiscountReserve, currentSelfSiteCost, currentCostsTotal, currentResult, currentIncome, currentLoss, currentIsLoss, rateHour, rateZero, rateWork, rateWorkFull, workHours, costHour, markup
- Загрузка: loadGoal, loadCur, loadZero (shoots, hours, days, freeDays, dayHours, shootsPerDay)
- Разбивка: depShoot, depOffice, depSoft, depEdu=0, depSite=0, depWs, varAds, varSoft, varBank, varRent, varAcc
- Инвестиции: ВЛОЖ, ЦЕЛЬ=ВЛОЖ/3, РЕКОМ, ФОНД.инв, ФОНД.реком, ФОНД.R, ФОНД.ручной
- Режим: regime, regimeCode (npd4/5/6, usn6/15, ausn8/20), clients, profession, NW, K, cl, curRate
- Минимумы: minShootsY, minShootsM, zeroShootsY, zeroShootsM
- Мост: PHR_D=d, PHR_CUSHION_Y, PHR_PROFIT_Y, parts()

### 1.3 Как передаётся
- saveReport(d) → localStorage['phc_report'] + _ts, saveState() → ['phc_state'] v=9
- Fallback: reportLink(d) → ?data=base64(JSON)
- report.html читает PHR_D из localStorage, если нет — DEMO (снимок без исключений, старый мир)

## Фаза 2 · Инвентарь report.html

### 2.1 Блоки (по data-block-id)
- B001 верхняя панель, B002 шапка, B003 главный экран (R, C, ставка), B004/B010/B017 благодарность, B005 из чего складывается цена, B007 бюджет (кольцо, 5 секторов при mgmtT>0, 4 при 0), B025 расходы (expenses), B026 резерв (vacY), B030 месячный доход (monC4), B028 накопления (отпуск, замена), B024 инвестиции (ВЛОЖ), B029 маржа (fundY→profit+buffer), B008 время (календарь, таблица недели, круг времени), B012 три сценария, B013 больше заказов, B009 скидка, B022 прайс допуслуг (PHR_PRINT), B011 налоговый режим, B021 амортизация камеры, B023 стоимость кадра (directFrameCosts?), B014 четыре цифры, B015 объяснение клиенту, B016 итоговое уведомление, B018 справочник, B019 пробный режим, B020 подвал, B006 логистика, B027 неэффективное время, B027 pce (details)

### 2.2 Что читает report из d
- B007: C, totalExpenses, depShoot, depOffice, depSoft, depWs, varAds, varSoft, varBank, varRent, varAcc, depEdu, depSite, wsY, siteY, eduY, amort, vari, R, Ny, fundY, fundP, discP, profitP, cushionShare, PHR_PROFIT_Y, PHR_CUSHION_Y, parts[11]=profit, [17]=buffer
- B008: NT, ND, EFF, pool, promo, accT, mgmtT, fmT, S, pt, py, sh, post, clT, idle, loadGoal/Cur/Zero, CAL, WEEKEND, HOLI, WD, VAC, SICK
- B021: camName, camPrice, camLife, camAmort, camWear, shotsYear, shPerHour, shLife
- B023: costHour, rateHour, depShoot? directFrameCosts (отсутствует в d — всегда fallback), frames
- B024: ВЛОЖ, eduSum+eduOpp, site_cost, equip, amort — via ФОНД.инв
- B025: totalExpenses, C, vari, amort, wsY, siteY, eduY
- B028: vacY, camAmort, shotsYear
- B029: fundY, fundP, cushionShare, profitP, PHR_PROFIT_Y, PHR_CUSHION_Y
- B030: monC4 = R/MO? (при mgmtT=0 — 0 ₽/мес дефект Д1)
- B012/B013: loadGoal, rateHour, minShootsY/M, zeroShootsY/M, cur, Rc, currentIncome/Loss
- B011: regime, regimeCode, taxAll, taxB, taxC, Rb, R, Rc
- DEMO: 22 поля расходятся с живым дефолтом (FormMgmt checked, Form024 checked, fund_on off, cushion_on off)

### 2.3 Мёртвые / полумёртвые
- fullTab (93 строки детального времени) — мёртв с 93e253b, никогда не рендерится (Д6)
- directFrameCosts — отсутствует в d (103 поля), B023 всегда запасная ветка (Д7)
- monC4, кружок 0,0, выноска NaN при mgmtT=0 (Д1-Д3)
- Легенда и таблица недели без управления при mgmtT=0 (Д4-Д5)
- Шкала роста док 5 vs код 4 (Д8)
- Form024 — 0 вхождений в report.html, деньги внутри C, сумма строк ≠ C (Н-07)
- eduY и siteY — считаются, но depEdu/depSite=0, в разбивке не видны как амортизация (верно по Н-08, но пользователь может искать)

## Фаза 3 · Матрица покрытия — что учтено, что нет

| Вопрос calc | Поле | В C? | В разбивке отчёта? | Отдельная строка? | Дефект |
|---|---|---|---|---|---|
| 07 client_time | clT | pool→sh | B008 таблица | да | нет |
| 08 promo | promo | side→gross | B008 | да | нет |
| 09 mgmt | mgmtT | side→gross, pool | B007 кольцо, B008 календарь/таблица | да, но при 0 — Д1-Д5 | Д1-Д5 |
| 10-11 техника | Form001/001b/002 | amort via sumF | B007, B021, B024, B025 | да (depShoot/depOffice) | нет, camAmort Σ |
| 12 софт | Form003/004 | vari/amort | B007 varSoft/depSoft | да | нет |
| 13 место | Form009b/013/013b | wsY/amort depWs | B007 varRent/depWs | да | нет |
| 14 обучение | Form006 eduY | C? нет, eduY отдельно, depEdu=0 | B024 ВЛОЖ включает eduSum+eduOpp, B007 0 | строка 0 — верно Н-08 | нет, но eduY не в C |
| 15 сайт | Form010 siteY | vari? siteY отдельно, depSite=0 | B024 ВЛОЖ включает site_cost, B007 0 | строка 0 — верно Н-08 | sdiv в D |
| 16 реклама | Form010 varAds | vari | B007 varAds | да | нет |
| 17 банк | Form007/012/015b varBank | vari | B007 varBank | да | нет |
| 18 учёт | Form011 accT/accM | side/vari | B008/B007 | да | нет |
| 18 сотрудники | Form024 | vari→C | нигде, 0 вхождений | нет — Н-07 | Н-07 |
| 19 fm | fmT | pool | B008 | да | нет |
| 20 disc | discP/discY | D→R | B009, B007? | да | нет |
| 21 cushion | cushionShare | profitP→fundY | B029 via PHR_CUSHION_Y | да, parts[17] | нет, прогон 24.09 ok |
| 22 fund | fundP | profitP→fundY | B029 via PHR_PROFIT_Y | да, parts[11] | нет, прогон ok |
| inv | ВЛОЖ | — | B024 | да | нет |

**Итог покрытия:** все кроме Form024 имеют строку. Form024 — единственный, кто входит в C, но не имеет своей строки в B007/B025. Это Н-07.

## Фаза 4 · Инварианты и проверки

- Инвариант 1: R = выручкаПод(Ny) при sh>0, D=1-a-sdiv-profitP-discP, D≥0.40, a≤0.10, discP≤0.15, profitP≤1, cushionShare≤1-fundP
- Инвариант 2 (28.09 revert): C = amort+vari, amort = equip+depWs, equip = sumF Form001+001b+002+004, vari = sumF Form003+010+007+012+024+accM+wsY = varAds+varSoft+varBank+varRent+varAcc+varEmp (6 форм, 5 групп+сотрудники), varEmp = sumF Form024 для детализации. Ранее 28.09 было C=amort+vari+varEmp без Form024 в vari.
- Инвариант 3: fundY = R*profitP, profit = R*fundP, buffer = fundY-profit = R*cushionShare, parts[11]+parts[17]=fundY
- Инвариант 4: pool = gross-fmT, gross = NT-side, side=promo+accT+mgmtT, side≤NT*0.8 (ПРЕДЕЛ_СТОРОННЕГО), sh = py*S, py=pool/pt, pt=S*M+cl, M=1+K
- Инвариант 5: workHours=ND*8, rateWork = (Ny*WM/MO)/workHours, rateWorkFull=R/NT, rateHour=R/sh
- Инвариант 6: camAmort = Σ Form001 price/life (исключённый каталог →0), camWear=camAmort/shotsYear
- Инвариант 7: DEMO vs live: 22 поля отличаются — DEMO не учитывает EXC FormMgmt checked, Form024 checked, fund_on off, cushion_on off, disc_on off, fm_on off
- Проверка харнессом: node харнесс.js '{"поля":{...},"EXC_ВНЕШ":{"FormMgmt":true,"Form024":true}}' → live.json, сверять R, C, fundY

## Фаза 5 · Дефекты и предложения (без правок, только наблюдение)

- Д1 monC4 0 ₽/мес 0.0% при mgmtT=0 — плашка остаётся
- Д2 кружок 0,0 в B007 при mgmtT=0
- Д3 выноска NaN при mgmtT=0
- Д4 легенда без управления при mgmtT=0
- Д5 таблица недели без управления
- Д6 fullTab мёртв 93 строки
- Д7 directFrameCosts отсутствует в d
- Д8 шкала роста док 5 vs код 4
- Д9 DEMO расходится с живым дефолтом 22 поля
- Н-07 Form024 нет строки
- Н-10 (новый): eduY и siteY не в C, но в ВЛОЖ — пользователь может искать их в расходах, сейчас 0 — верно по слову 23.09, но требует пояснения в B025

## Фаза 6 · Новая дорожная карта сведения (очередь после Н-01…Н-09)

| Шаг | Что | Как проверить | Критерий приёмки |
|---|---|---|---|
| С-01 | Снять живой дефолт (с EXC FormMgmt, Form024) в live.json и сравнить с DEMO | харнесс + diff 22 полей | список расхождений зафиксирован |
| С-02 | Проверить mgmtT=0 путь — все 5 дефектов Д1-Д5 воспроизвести | calc с FormMgmt checked, открыть report | скриншоты 0 ₽/мес, 0,0, NaN |
| С-03 | Проверить fund_on+cushion_on путь — разделение profit/buffer | харнесс fund_on 18% + cushion 10% → live_fund.json, probe mpBody | mpBody 498 302 ₽/год, parts[11]+[17]=fundY |
| С-04 | Проверить Form024 путь — деньги в C, но нет строки | харнесс Form024 off (включены сотрудники) vs on | C отличается на сумму сотрудников, в report 0 вхождений |
| С-05 | Проверить fullTab и directFrameCosts — мёртвые ветки | grep fullTab, grep directFrameCosts в report | подтвердить Д6, Д7 |
| С-06 | Сверить ВЛОЖ и ЦЕЛЬ — eduSum+eduOpp+site_cost входят | calc ВЛОЖ vs B024 | совпадает |
| С-07 | Сверить инварианты R, C, D, fundY | calc формулы vs report PHR_D | все 7 инвариантов зелёные |
| С-08 | Предложение по Н-07 — строка сотрудников | написать 2 варианта: оставить внутри C с пояснением vs завести строку | ждать слово «делаем Н-07» |
| С-09 | Предложение по Д1-Д5 — скрывать плашку monC4 при mgmtT=0 или показывать 0 как задумано | написать вариант | ждать слово |
| С-10 | Обновить DEMO — пересобрать из живого дефолта | после приёмки Н-07 и Д1-Д5 | DEMO = live |

Правило 16: без команды «делаем С-XX» правок нет. Только съём и предложения.

## Прогресс на 25.09
- С-01 ✔ — живой дефолт снят, 28 расхождений DEMO vs live зафиксированы (`С-01`)
- С-02 ✔ — mgmtT=0 дефекты Д1-Д5 воспроизведены jsdom (`С-02`)
- С-03 ✔ — fund_on+cushion_on прогон 498 302 + 276 834, mpBody корректно (`С-03`)
- С-04 ✔ — Form024 входит в C на 360k, но 0 вхождений в report, сумма строк не сходится (`С-04`) → решено в Н-07 вариант Б
- С-05 ✔ — fullTab мёртв 93 строки, directFrameCosts отсутствует, всегда fallback (`С-05`)
- Н-07 ✔ 25.09 вариант Б — varEmp добавлен, parts[18]=360k, lg2 показывает 1 712 ₽/час, без сотрудников прячется
- С-06 ✔ 25.09 — ВЛОЖ и ЦЕЛЬ сверка: дефект B024 — не учитывался b=13 (обустройство 82 500 ₽). Фикс: в `report.html` добавлен `обустройство` в расчёт `итог = съём+пост+обустройство+время`, `инвПост` теперь `пост+обустройство`. После фикса `инвИтого=1 442 125 ₽` совпадает с calc `ВЛОЖ=1 442 125`, ЦЕЛЬ=480 708 (ВЛОЖ/3), РЕКОМ=20% (выручкаПод(Ny+ЦЕЛЬ)). Проверка: jsdom + харнесс HARNESS_FOND=1.
- С-07 ✔ 25.09 — инварианты: R=2 768 346, C=457 454=amort 173 474+vari 283 980, a=0.027, D=0.693=1-a-profitP-discP (profitP=0.28 fundP 0.18+cushion 0.10), fundY=775 136=R*profitP, ЦЕЛЬ=480 708. PHR_D в report совпадает с харнессом. Правило 40% D соблюдено.
- С-08 ✔ — Н-07 закрыт
- С-09 ⏸ — предложение Д1-Д5 скрывать 0 сектор управления в B030
- С-10 ⏸ — обновить DEMO после приёмки Д1-Д5

## Прогресс на 28.09 — коррекция группировки по паспортам (слово владельца 27.09) + revert 28.09 по решению inside_vari + обновление Состав vari по слову владельца
- Регулярные расходы специалиста = только финансовые (vari), Временные расходы (workHours) = отдельная строка, без управления делом. Решение владельца 28.09: keep_current.
- Наёмные сотрудники Form024 — регулярный финансовый расход, внутри vari. Решение владельца 28.09: inside_vari — вернуть как было до 28.09.
- Правка `Веб/calc.html` 28.09 revert: `varEmp=sumF('Form024')`, `vari=sumF('Form003')+sumF('Form010')+sumF('Form007')+sumF('Form012')+varEmp+accM+wsY`, `C=amort+vari`. Теперь default vari=283980 (5 групп без сотрудников, т.к. Form024 checked по умолчанию), с сотрудником 30k*12 vari=643980 = 283980+360000, C=817454, varEmp=360000 для детализации.
- Проверка харнессом: default vari=283980 varEmp=0 C=457454; с сотрудником 30k*12 vari=643980 varEmp=360000 C=817454, C=amort+vari true.
- **Глоссарий обновлён (по слову владельца, без хаотичных документов):** добавлен №151 «Наёмные сотрудники» — «Физические лица, которые заключили трудовой договор с работодателем (компанией, организацией или индивидуальным предпринимателем) и выполняют для него определенную трудовую функцию за регулярную заработную плату, подчиняясь внутреннему трудовому распорядку.»
- **Состав vari обновлён (по слову владельца):** лист `Состав` строка vari теперь 6 позиций: Подписки, Реклама, Банковское обслуживание, Бухгалтерия, Содержание рабочего места, Наёмные сотрудники. Ранее было 5 без сотрудников. Form012 (кредиты) остаётся внутри Банковского обслуживания (varBank=Form007+Form012) — calc.html структурирован по блокам, блок 16 (банк) и блок 18 (сотрудники) оба в секции Расходы, перетасовки не нужны.
- Остаток: паспорт vari (26.08) — 5 позиций без Form012 и без Form024, требует обновления после подтверждения (паспорт создаётся только после слова владельца, по регламенту). Паспорт Финансовые расходы — аналогично. Отдельный документ ИСПРАВЛЕНИЕ_28_09 удалён по правилу «без подтверждения не создавать».
- `Веб/report.html` t03: Регулярные включают сотрудников (когда включены), Наёмные отдельной строкой для прозрачности — сумма строк сходится, vari включает varEmp.

## Прогресс на 25.09 вечер — фикс B024 баннер + перенос B029
- B024 «Вы вложили в своё дело» сломан: причина — предыдущий фикс превью вставил JS-конкатенацию `"'+` внутри атрибута `src=\"data:image/webp;base64,...\"`, что ломало картинку (src содержал `"+`). Фикс: заменить `<img src=\"data:...\">` на `<img id=\"invScene\">` без src, добавить скрипт сборки `b64` из 34 чанков по 8KB (`b64 = 'chunk1'+'chunk2'+...`), затем `img.src='data:image/webp;base64,'+b64`. Проверка jsdom: src len 269332, инвИтого 1 442 125 ₽, longest line 22141.
- B029 «Ваше дело принесёт чистую прибыль» перенесён после B026 «Отложите в резерв» по слову владельца: вырезан блок `<div id=\"mpHost\" REPORT-B029><div id=\"mpBody\"></div></div><div id=\"mpZero\"></div>` и вставлен сразу после `card01r` (B026). Новый порядок: B026(03) → B029 → B030(04) → B028 → B024 → B008(06) → B012(07) → B013(08). Проверка: mpBody «Ваше дело принесёт чистую прибыль 498 302 ₽/год».

## Следующий шаг по §2.11
С-06, С-07 закрыты, B024 баннер починен, B029 перенесён после резерва. Остаток: С-09 — предложение Д1-Д5 (скрывать 0 сектор управления в B030/кольце), С-10 — обновить DEMO после приёмки Д1-Д5. Ждёт слова владельца.
