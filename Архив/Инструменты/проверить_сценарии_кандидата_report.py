#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Рендерит кандидата report с настоящими данными calc() в 16 сценариях."""
from pathlib import Path
from tempfile import NamedTemporaryFile
import json,math,subprocess
ROOT=Path(__file__).resolve().parents[1]; CAND=ROOT/'Веб'/'Кандидаты'/'report.html'
scenarios=[
 ('НПД 4%',{'поля':{'regime':'npd','npd_who':'phys'}}),('НПД 5%',{'поля':{'regime':'npd','npd_who':'mix'}}),
 ('НПД 6%',{'поля':{'regime':'npd','npd_who':'jur'}}),('УСН 6%',{'поля':{'regime':'usn6'}}),
 ('УСН 15%',{'поля':{'regime':'usn15'}}),('АУСН 8%',{'поля':{'regime':'ausn8'}}),('АУСН 20%',{'поля':{'regime':'ausn20'}}),
 ('Налоги выключены',{'поля':{'tax_off':True}}),('Резервы включены',{'поля':{'fund_on':True,'disc_on':True}}),
 ('Сайт самостоятельно',{'радио':{'site_mode':'self'}}),('Дополнительная комиссия',{'допКомиссии':1.5}),
 ('Собственное жильё',{'поля':{'own_home':True}}),('Рабочее место исключено',{'EXC_ВНЕШ':{'Form009b':True}}),
 ('Обучение исключено',{'EXC_ВНЕШ':{'Form006':True}}),('Сайт исключён',{'EXC_ВНЕШ':{'Form014':True}}),
 ('Убыток',{'поля':{'current_rate':'1000'}}),
]
def num(n):return f'{round(n):,}'.replace(',','')
for title,override in scenarios:
 d=json.loads(subprocess.check_output(['node',str(ROOT/'Инструменты'/'харнесс.js'),str(ROOT),json.dumps(override,ensure_ascii=False)],text=True))
 d.pop('__parts',None)
 with NamedTemporaryFile('w',suffix='.json',encoding='utf-8',delete=False) as f:
  json.dump(d,f,ensure_ascii=False); path=f.name
 try:
  raw=subprocess.check_output(['node',str(ROOT/'Инструменты'/'проверить_рендер_report.js'),str(CAND),path],text=True)
 finally:Path(path).unlink(missing_ok=True)
 out=json.loads(raw); text=''.join(out['scenarios'].split())
 if out['errors']:raise SystemExit(f'{title}: JS ошибки {out["errors"]}')
 expected=[num(d['curRate']),num(d['rateHour']),num(d['rateZero']),num(d['R']/12),num(d['Rb']/12),str(math.ceil(d['zeroShootsM']))]
 missing=[x for x in expected if x not in text]
 if missing:raise SystemExit(f'{title}: в карточках нет {missing}')
 if d['currentResult']<0:
  if 'Убыток' not in out['scenarios'] or num(abs(d['currentResult']/12)) not in text:raise SystemExit(f'{title}: убыток не показан')
 print('✓',title)
# Отдельно рендерим все контрольные ветки программы лояльности.
loyalty_cases=[('5%',{'disc_on':True,'disc_pct':'5'}),('10%',{'disc_on':True,'disc_pct':'10'}),
               ('15%',{'disc_on':True,'disc_pct':'15'}),('5%, съёмка 6 ч',{'disc_on':True,'disc_pct':'5','shoot_manual':'6'}),
               ('5%, съёмка 8 ч',{'disc_on':True,'disc_pct':'5','shoot_manual':'8'})]
for title,fields in loyalty_cases:
 d=json.loads(subprocess.check_output(['node',str(ROOT/'Инструменты'/'харнесс.js'),str(ROOT),json.dumps({'поля':fields},ensure_ascii=False)],text=True));d.pop('__parts',None)
 with NamedTemporaryFile('w',suffix='.json',encoding='utf-8',delete=False) as f:
  json.dump(d,f,ensure_ascii=False);path=f.name
 try:out=json.loads(subprocess.check_output(['node',str(ROOT/'Инструменты'/'проверить_рендер_report.js'),str(CAND),path],text=True))
 finally:Path(path).unlink(missing_ok=True)
 text=''.join(out['loyalty'].split())
 if out['errors'] or not text or num(d['discY']) not in text:raise SystemExit(f'Лояльность {title}: фонд не отрендерен')
 if 'Сверхтогосэкономите' in text or 'освободитерабочеговремени' in text:raise SystemExit(f'Лояльность {title}: вернулась неподтверждённая экономия')
 print('✓ Лояльность',title)
print(f'Кандидат report: {len(scenarios)} общих и {len(loyalty_cases)} сценариев лояльности отрендерено, расхождений 0')
