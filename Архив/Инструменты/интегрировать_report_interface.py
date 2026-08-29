#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает кандидата report из визуального исходника ветки interface.

Рабочий report не изменяет. В кандидат переносятся только актуальные данные,
контракт, справочник и технические ID основной ветки.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Архив'/'Вёрстка'/'report_interface_a237c8b_исходник.html'
CURRENT=ROOT/'Веб'/'report.html'
OUT_DIR=ROOT/'Веб'/'Кандидаты'
OUT=OUT_DIR/'report.html'; KARKAS=OUT_DIR/'каркас.html'
visual=SOURCE.read_text(encoding='utf-8'); current=CURRENT.read_text(encoding='utf-8')

def function(text,name):
    start=text.index('function '+name+'('); brace=text.index('{',start); level=0; quote=None; esc=False
    for i in range(brace,len(text)):
        ch=text[i]
        if quote:
            if esc:esc=False
            elif ch=='\\':esc=True
            elif ch==quote:quote=None
            continue
        if ch in "'\"`":quote=ch
        elif ch=='{':level+=1
        elif ch=='}':
            level-=1
            if level==0:return text[start:i+1]
    raise ValueError(name)

def replace_function(dst,src,name):
    return dst.replace(function(dst,name),function(src,name),1)

def var_array(text,marker):
    start=text.index(marker); bracket=text.index('[',start); level=0;quote=None;esc=False
    for i in range(bracket,len(text)):
        ch=text[i]
        if quote:
            if esc:esc=False
            elif ch=='\\':esc=True
            elif ch==quote:quote=None
            continue
        if ch in "'\"`":quote=ch
        elif ch=='[':level+=1
        elif ch==']':
            level-=1
            if level==0:
                end=text.index(';',i)+1
                return text[start:end]
    raise ValueError(marker)

# 1. Техническая разметка страницы и 20 прямых блоков новой структуры.
visual=visual.replace('<div id="phr-root">','<div id="phr-root" data-page-id="PAGE-REPORT">',1)
blocks=[
 ('<div class="tbar" id="topbar">','REPORT-B001','Верхняя панель'),
 ('<div class="hdr">','REPORT-B002','Шапка отчёта'),
 ('<div class="hwrap">','REPORT-B003','Главный экран'),
 ('<div class="savebar top">','REPORT-B004','Поблагодарить проект — верх'),
 ('<div class="wnote">','REPORT-B005','Из чего складывается цена'),
 ('<div class="logi">','REPORT-B006','Логистика'),
 ('<div class="card" id="card01">','REPORT-B007','Как распределяется бюджет'),
 ('<div class="card" id="card02">','REPORT-B008','Как распределяется время'),
 ('<div class="card" id="card06">','REPORT-B009','Скидка'),
 ('<div class="thxbar">','REPORT-B010','Поблагодарить проект — середина'),
 ('<div class="card" id="card07">','REPORT-B011','Налоговый режим'),
 ('<div class="card" id="card04">','REPORT-B012','Три сценария работы'),
 ('<div class="card" id="card05">','REPORT-B013','Больше заказов'),
 ('<div class="card" id="card09" data-thx-авто>','REPORT-B014','Четыре цифры'),
 ('<div class="card" id="card10">','REPORT-B015','Объяснение стоимости клиенту'),
 ('<div class="logi logiw">','REPORT-B016','Итоговое уведомление'),
 ('<div class="cta thx">','REPORT-B017','Финальная благодарность'),
 ('<div id="спрдет">','REPORT-B018','Справочник и детализация'),
 ('<div class="trb" id="trial">','REPORT-B019','Пробный режим'),
 ('<div class="foot">','REPORT-B020','Подвал'),
]
for tag,bid,name in blocks:
    if tag not in visual: raise SystemExit('Не найден блок: '+tag)
    visual=visual.replace(tag,tag[:-1]+f' data-block-id="{bid}" data-block-name="{name}">',1)

# 2. DEMO и справочник — только из текущего рабочего report.
demo_re=r'(/\* ДЕМО[^*]*\*/\n)?var DEMO=\{.*?\};'
mcur=re.search(demo_re,current,re.S); mvis=re.search(demo_re,visual,re.S)
if not mcur or not mvis: raise SystemExit('Не найден DEMO')
visual=visual[:mvis.start()]+mcur.group(0)+visual[mvis.end():]
visual=visual.replace(var_array(visual,'var REFD=['),var_array(current,'var REFD=['),1)
spr_re=r'var СПР = \[.*?\];\n'
visual,n=re.subn(spr_re,re.search(spr_re,current,re.S).group(0),visual,count=1,flags=re.S)
if n!=1: raise SystemExit('Не заменён СПР')
# Карты ссылок справочника генерируются одной строкой.
line_cur=re.search(r'^var СВЯЗЬ_05 = .*?;$',current,re.M).group(0)
visual,n=re.subn(r'^var СВЯЗЬ_05 = .*?;$',lambda m:line_cur,visual,count=1,flags=re.M)
if n!=1: raise SystemExit('Не заменены СВЯЗЬ')

# 3. Кольцо использует полную современную разбивку без удалённых equip/promoM.
visual=replace_function(visual,current,'parts')

# 4. Удаляем неподтверждённую экономию постоянного клиента и 0,70.
visual=visual.replace('Источник правды — книга, лист 13b_Программа_лояльности.',
                      'Расчётная спецификация — основная книга, лист Программа_лояльности.')
# Стили удалённых числовых плашек экономии больше не нужны.
visual=re.sub(r'#phr-root \.sc3 \.s3t\{.*?@media\(max-width:700px\)\{#phr-root \.sc3 \.s3t\{grid-template-columns:1fr\}\}\n','',visual,count=1,flags=re.S)
start=visual.find('  /* --- стоимость привлечения клиента ---')
end=visual.find('  var зп=d.discP||0',start)
if start>=0 and end>start: visual=visual[:start]+visual[end:]
visual=re.sub(r'\s*/\* выгода сверх скидок:.*?var годЭк=.*?;\n','\n',visual,count=1,flags=re.S)
visual=re.sub(r"\s*'<div class=\"s3t\">'.*?'</div>'\+\n",'\n',visual,count=1,flags=re.S)
visual=visual.replace('Все скидки постоянным клиентам полностью покрываются фондом программы лояльности. Сэкономленные на привлечении деньги и освободившееся время в расчёт скидок не заложены — это ваша чистая выгода, распорядитесь ею по своему усмотрению.<br>Доля повторных заказов взята по отраслевой норме — такой показатель считается хорошим результатом работы с клиентской базой. Распределение по частоте визитов приведено как пример, оно опирается на ступени вашей скидки постоянному клиенту.',
'Все скидки постоянным клиентам полностью покрываются фондом программы лояльности. Возможная экономия на привлечении пока не используется для финансирования скидок: для её расчёта нужны фактические данные специалиста. Распределение по частоте визитов приведено как пример и опирается на ступени скидки постоянному клиенту.')
visual=visual.replace('Постоянный клиент экономит вам самое ценное — время на поиск новых заказчиков, долгие созвоны и согласования. Его не нужно заново убеждать в качестве, он уже знает все правила и приходит с готовой задачей.<span class="exm">Вы сэкономите:</span><span class="exl"><b>от 30% вашего бюджета</b> — сможете увеличить личный доход или направить его на развитие;</span><span class="exl"><b>до 20% вашего рабочего времени</b> — которое вы можете потратить на отдых, семью или взять ещё одну коммерческую съёмку.</span>',
'Постоянные клиенты помогают формировать более стабильный поток заказов. Возможную экономию на привлечении Счётикс пока не переводит в деньги или часы: для этого нужны фактические данные о рекламе, обращениях, повторных заказах и времени на коммуникацию.')

# 5. Актуальные названия сценариев и дополнительный показатель «В ноль».
visual=visual.replace("no:'\\u0420\\u0435\\u0430\\u043b\\u044c\\u043d\\u044b\\u0439 \\u0441\\u0446\\u0435\\u043d\\u0430\\u0440\\u0438\\u0439'","no:'\\u0442\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439'",1)
visual=visual.replace("no:'\\u0418\\u0434\\u0435\\u0430\\u043b\\u044c\\u043d\\u044b\\u0439 \\u0441\\u0446\\u0435\\u043d\\u0430\\u0440\\u0438\\u0439'","no:'\\u0436\\u0435\\u043b\\u0430\\u0435\\u043c\\u044b\\u0439'",1)
visual=visual.replace("no:'\\u0421\\u0446\\u0435\\u043d\\u0430\\u0440\\u0438\\u0439 \\u0432 \\u043d\\u043e\\u043b\\u044c'","no:'\\u0432 \\u043d\\u043e\\u043b\\u044c'",1)
visual=visual.replace("t:'\\u041d\\u0435\\u043e\\u0431\\u0445\\u043e\\u0434\\u0438\\u043c\\u044b\\u0439 \\u0434\\u043e\\u0445\\u043e\\u0434'","t:'\\u0416\\u0435\\u043b\\u0430\\u0435\\u043c\\u044b\\u0439 \\u0434\\u043e\\u0445\\u043e\\u0434'",1)
visual=visual.replace("t:currentIsLoss?'\\u0423\\u0431\\u044b\\u0442\\u043e\\u043a':'\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u0434\\u043e\\u0445\\u043e\\u0434'","t:currentIsLoss?'\\u0412\\u0430\\u0448 \\u0443\\u0431\\u044b\\u0442\\u043e\\u043a':'\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u0434\\u043e\\u0445\\u043e\\u0434'",1)
visual=visual.replace('r:f0(bRateV), rev:f0(Vb/12),\n     v:[0,Vb]', 'r:f0(bRateV), rev:f0(Vb/12), shoots:Math.ceil(d.zeroShootsM||0),\n     v:[0,Vb]',1)
# Визуальная карточка З-148 сохраняется; добавляем только строку количества.
needle="'<div class=\"revrow\"><span>\\u041e\\u0431\\u0449\\u0430\\u044f \\u0432\\u044b\\u0440\\u0443\\u0447\\u043a\\u0430</span><b>'+x.rev+'/\\u043c\\u0435\\u0441</b></div>'+\n"
if needle in visual:
    visual=visual.replace(needle,needle+"    (x.shoots?'<div class=\"zero-shoots\"><b>'+x.shoots+' '+скл(x.shoots,'съёмка','съёмки','съёмок')+'</b><span>в месяц, чтобы покрыть расходы при этой ставке</span></div>':'')+\n",1)
# В принятом решении знак минус в карточках Скидки за объём не выводится.
visual=visual.replace("'<div class=\"dpr disc\">\\u2212'+f1(c.dd*100)+'%</div>'+",
                      "'<div class=\"dpr disc\">'+f1(c.dd*100)+'%</div>'+",1)
# Новая карточка З-148 раньше не имела строки zeroShootsM.
zero_css='''\n#phr-root .zero-shoots{margin:10px 16px 0;padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.64);text-align:center}\n#phr-root .zero-shoots b{display:block;font-size:17px;color:var(--c-ig-2)}\n#phr-root .zero-shoots span{display:block;margin-top:3px;font-size:11.5px;line-height:1.3;color:var(--gr)}\n'''
visual=visual.replace('</style>',zero_css+'</style>',1)

# 6. Терминология агрегатов и главного результата.
visual=visual.replace('Ваша ставка за час съёмки','Ваша желаемая ставка за час съёмки',1)
visual=visual.replace('Налоги и страховые взносы / год','Налоги и Страховые взносы / год')
visual=visual.replace('Эквайринг / год','Эквайринг и дополнительные банковские комиссии / год')
visual=visual.replace("'Налоги и страховые взносы / год'","'Налоги и Страховые взносы / год'")
visual=visual.replace("'Эквайринг / год'","'Эквайринг и дополнительные банковские комиссии / год'")

# Защита первого этапа.
for bad in ['перепЧ*0.70','Сверх того сэкономите на привлечении','от 30% вашего бюджета','до 20% вашего рабочего времени']:
    if bad in visual: raise SystemExit('Остался запрещённый фрагмент: '+bad)
if visual.count('data-block-id=')!=20: raise SystemExit('Ожидалось 20 data-block-id')
if 'data-page-id="PAGE-REPORT"' not in visual: raise SystemExit('Нет PAGE-REPORT')

OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT.write_text(visual,encoding='utf-8'); KARKAS.write_text(visual,encoding='utf-8')
print(f'Кандидат собран: {OUT}; {len(visual.encode())} байт; 20 блоков')
