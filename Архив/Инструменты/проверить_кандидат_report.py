#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет кандидата новой вёрстки без замены рабочего report."""
from pathlib import Path
from bs4 import BeautifulSoup,Tag
import json,re,subprocess,sys,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'Веб'/'Кандидаты'/'report.html'; KARKAS=ROOT/'Веб'/'Кандидаты'/'каркас.html'; CUR=ROOT/'Веб'/'report.html'
a=CAND.read_text(); k=KARKAS.read_text(); cur=CUR.read_text(); errors=[]
def check(cond,msg):
    if not cond: errors.append(msg)
check(a==k,'кандидат не совпадает с каркасом')
soup=BeautifulSoup(a,'html.parser'); root=soup.select_one('#phr-root'); wp=soup.select_one('.wp')
children=[x for x in wp.children if isinstance(x,Tag)] if wp else []
ids=re.findall(r'data-block-id="([^"]+)"',a)
check(root and root.get('data-page-id')=='PAGE-REPORT','нет PAGE-REPORT')
check(len(children)==20,'прямых блоков .wp не 20')
check(len(ids)==20 and len(set(ids))==20,'data-block-id не 20 уникальных')
check(len({x.get('id') for x in soup.select('[id]')})==len(soup.select('[id]')),'есть повторные DOM-ID')
# Контракт потребителей должен совпадать с текущим рабочим отчётом.
d=lambda s:set(re.findall(r'\bd\.([A-Za-z_]\w*)',s))
check(d(a)==d(cur),'набор используемых полей d отличается от рабочего report')
# DEMO и пользовательский справочник переносятся дословно.
demo=r'(/\* ДЕМО[^*]*\*/\n)?var DEMO=\{.*?\};'
check(re.search(demo,a,re.S).group(0)==re.search(demo,cur,re.S).group(0),'DEMO отличается')
spr=r'var СПР = \[.*?\];\n'
check(re.search(spr,a,re.S).group(0)==re.search(spr,cur,re.S).group(0),'СПР отличается')
for bad in ['перепЧ*0.70','Сверх того сэкономите на привлечении','от 30% вашего бюджета','до 20% вашего рабочего времени','d.core','d.sAuto','d.equip','d.promoM','d.side']:
    check(bad not in a,'вернулся запрещённый фрагмент '+bad)
check('d.zeroShootsM' in a,'нет zeroShootsM')
check('Налоги и Страховые взносы / год' in a,'старое название Налогов')
check('Эквайринг и дополнительные банковские комиссии / год' in a,'старое название банковских комиссий')
# JS компилируется.
js='\n'.join(x.get_text() for x in soup.find_all('script'))
p=subprocess.run(['node','-e','new Function(require("fs").readFileSync(0,"utf8"))'],input=js,text=True,capture_output=True)
check(p.returncode==0,'JS не компилируется: '+(p.stderr.splitlines()[0] if p.stderr else ''))
# Настоящий calc() с parts() кандидата сходится.
with tempfile.TemporaryDirectory() as td:
    td=Path(td); (td/'Веб').mkdir(); shutil.copy2(ROOT/'Веб'/'calc.html',td/'Веб'/'calc.html'); shutil.copy2(CAND,td/'Веб'/'report.html')
    p=subprocess.run(['node',str(ROOT/'Инструменты'/'харнесс.js'),str(td)],capture_output=True,text=True)
    if p.returncode: errors.append('харнесс кандидата не запустился')
    else:
        data=json.loads(p.stdout); check(abs(sum(data['__parts'])-data['R'])<.01,'кольцо кандидата не сходится')
if errors:
    print('\n'.join('✗ '+x for x in errors));sys.exit(1)
print('Кандидат report: базовая интеграция пройдена · 20 блоков · контракт и справочник актуальны')
