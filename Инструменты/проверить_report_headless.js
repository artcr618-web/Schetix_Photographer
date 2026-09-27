#!/usr/bin/env node
/* Постоянная jsdom-проверка настоящего report.html по нескольким сценариям. */
const fs=require('fs'), path=require('path'), cp=require('child_process');
let JSDOM,VirtualConsole;
try{({JSDOM,VirtualConsole}=require('jsdom'))}catch(e){
  console.error('Не установлен jsdom. Выполните npm ci в папке Инструменты.');process.exit(3);
}
const ROOT=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const REPORT=path.join(ROOT,'Веб','report.html');
const HARNESS=path.join(ROOT,'Инструменты','харнесс.js');
const BROWSER_DEFAULT=path.join(ROOT,'Инструменты','проверить_calc_browser_default.js');
const html=fs.readFileSync(REPORT,'utf8');

function calculation(override){
  const p=cp.spawnSync('node',[HARNESS,ROOT,JSON.stringify(override||{})],{encoding:'utf8'});
  if(p.status!==0)throw Error('харнесс: '+(p.stderr||p.stdout).trim().slice(0,300));
  const d=JSON.parse(p.stdout);delete d.__parts;d._ts=Date.now();return d;
}
/* «default» обязан пройти настоящий жизненный цикл calc.html: EXC из data-exc,
   автоматический fund_pct и смену НПД по лимиту. Другие сценарии ниже —
   намеренно synthetic-переопределения харнесса. */
function browserDefault(){
  const p=cp.spawnSync('node',[BROWSER_DEFAULT,ROOT,'--assert','--result'],{encoding:'utf8'});
  if(p.status!==0)throw Error('browser default: '+(p.stderr||p.stdout).trim().slice(0,300));
  const d=JSON.parse(p.stdout);d._ts=Date.now();return d;
}
function assert(list,cond,msg){if(!cond)list.push(msg)}
function text(el){return el?el.textContent.replace(/\s+/g,' ').trim():''}
function wait(ms){return new Promise(r=>setTimeout(r,ms))}

async function render(name,override){
  const errors=[],vc=new VirtualConsole();let ignoredPageMarginCss=0;
  vc.on('jsdomError',e=>{if(e.message==='Could not parse CSS stylesheet')ignoredPageMarginCss++;else errors.push(e.message)});vc.on('error',e=>errors.push(String(e)));
  const injected=override===null?null:((name==='default'||name==='query')?browserDefault():calculation(override));
  /* calc.html передаёт d двумя путями: localStorage и кодированным ?data=.
     Проверяем оба настоящим рендером отчёта, а не только наличием строк в коде. */
  const throughQuery=name==='query';
  const url='https://schetix.test/report.html'+(injected
    ? (throughQuery ? '?data='+encodeURIComponent(Buffer.from(JSON.stringify(injected),'utf8').toString('base64')) : '')
    : '?demo=1');
  const dom=new JSDOM(html,{url,
    runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
      if(injected&&!throughQuery)w.localStorage.setItem('phc_report',JSON.stringify(injected));
      w.scrollTo=()=>{};
      w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
      w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};
      w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
      if(!w.URL.createObjectURL)w.URL.createObjectURL=()=>'';
      if(!w.URL.revokeObjectURL)w.URL.revokeObjectURL=()=>{};
    }});
  await wait(900);
  const d=dom.window.document,fail=[];
  const ids=[...d.querySelectorAll('[data-block-id]')].map(x=>x.dataset.blockId);
  assert(fail,errors.length===0,'ошибки JS: '+errors.join(' | '));
  assert(fail,ignoredPageMarginCss<=1,'неожиданные ошибки CSS: '+ignoredPageMarginCss);
  assert(fail,d.querySelector('#phr-root')?.dataset.pageId==='PAGE-REPORT','нет PAGE-REPORT');
  assert(fail,ids.length===30&&new Set(ids).size===30,`не 30 уникальных блоков: ${ids.length}/${new Set(ids).size}`);
  const wp=d.querySelector('.wp'), children=wp?[...wp.children]:[];
  assert(fail,children.length===31,`не 31 прямой блок .wp: ${children.length}`);
  const profitAt=children.indexOf(d.querySelector('#mpHost')),
        priceAt=children.indexOf(d.querySelector('[data-block-id="REPORT-B005"]'));
  assert(fail,profitAt>=0 && priceAt===profitAt+2 && children[profitAt+1]?.id==='mpZero',
         'B029 должен стоять непосредственно над B005');
  assert(fail,text(d.querySelector('#dns')).length>100,'не отрисованы три сценария');
  /* 15.09 (слово владельца): блок 06 получил таблицу времени по
     периодам — 12 → 13. */
  assert(fail,d.querySelectorAll('table').length===13,'ожидалось 13 таблиц');
  assert(fail,d.querySelectorAll('table tbody tr').length>=150,'меньше 150 строк таблиц');
  assert(fail,text(d.querySelector('#спрдет')).length>20000,'не собрана детализация/справочник');
  assert(fail,d.querySelector('#dn1 svg')!==null,'не построена диаграмма бюджета');
  assert(fail,d.querySelector('#wk')?.children.length>0,'не построен недельный график');
  /* B008: линейная расшифровка не скрывает нулевые роли — исключение
     остаётся только для кольцевых диаграмм. */
  const timeLegend=text(d.querySelector('#wklg')),
        timeRows=[...d.querySelectorAll('#wtBd tr')],
        timeTable=text(d.querySelector('#wtBd')),
        weekGrids=[...d.querySelectorAll('#wk > .wk-week')],
        expectedWeeks=Math.max(1,Math.round(injected?.projectPlan?.weeks||weekGrids.length||1));
  /* B008: один календарный блок содержит все компактные недели плана
     одновременно. Внутри каждой сетки — заголовок + 11 строк 09:00–20:00. */
  assert(fail,weekGrids.length===expectedWeeks,
    'B008: число видимых недель не совпадает с готовым планом calc.html');
  assert(fail,(expectedWeeks>1)===d.querySelector('#wk')?.classList.contains('wk-plan'),
    'B008: класс многонедельного календаря не соответствует плану');
  assert(fail,weekGrids.every(grid=>grid.children.length===72),
    'B008: хотя бы одна неделя не содержит 11 часовых строк с 09:00 до 20:00');
  function wkCell(hour,day,week=0){
    const cells=weekGrids[week]?[...weekGrids[week].children]:[];
    return cells[6+(hour-9)*6+1+day]?.querySelector('i');
  }
  function cellHas(hour,day,label,week=0){
    return (wkCell(hour,day,week)?.title||'').split(' · ').includes(label);
  }
  const officeMode=!!injected&&(injected.answers||[]).some(a=>Number(a.b)===13&&a.n==='Где находится рабочее место'&&a.v==='Отдельное помещение');
  for(let week=0;week<weekGrids.length;week++)for(let day=0;day<5;day++)
    assert(fail,wkCell(14,day,week)?.title==='Обед','B008: обед 14:00–15:00 не поставлен в неделю '+(week+1)+', день '+day);
  const legendTitle=d.querySelector('#card02 .slg-h');
  assert(fail,text(legendTitle)==='Условные обозначения',
         'B008: над легендой нет заголовка «Условные обозначения»');
  const legendHeads=[...d.querySelectorAll('#wklg .slg-t')],
        hiddenHead=legendHeads.find(x=>text(x)==='Скрытая работа'),
        unpaidHead=legendHeads.find(x=>text(x)==='Неоплаченное время'),
        hiddenNote=hiddenHead?.parentElement.querySelector('.slg-note'),
        unpaidNote=unpaidHead?.parentElement.querySelector('.slg-note');
  /* Название группы — единственная жирная часть. Пояснение — обычным
     текстом в скобках; двоеточие оставлено после закрывающей скобки. */
  assert(fail,!!hiddenHead&&text(hiddenHead)==='Скрытая работа','B008: заголовок «Скрытая работа» изменён или получил двоеточие');
  assert(fail,!!unpaidHead&&text(unpaidHead)==='Неоплаченное время','B008: заголовок «Неоплаченное время» изменён или получил двоеточие');
  assert(fail,text(hiddenNote)==='(не оплачивается напрямую, но входит в состав стоимости съёмочного часа):',
    'B008: не объяснено, как скрытая работа входит в стоимость, или пропало двоеточие');
  assert(fail,text(unpaidNote)==='(не входит в стоимость съёмочного часа, но всегда выделяется):',
    'B008: нет ясного статуса неоплаченного времени или двоеточия');
  assert(fail,hiddenNote?.tagName==='SPAN'&&unpaidNote?.tagName==='SPAN',
    'B008: пояснение легенды ошибочно выделено как заголовок');
  assert(fail,timeLegend.includes('Обед — 14:00–15:00'),'B008: в легенде нет отдельного обеда');
  assert(fail,timeLegend.includes(officeMode
    ? 'Логистика — 1 ч до начала и 1 ч после окончания рабочего дня'
    : 'Логистика — 1 ч до и 1 ч после съёмки'),'B008: в легенде нет корректного режима логистики');
  if(!officeMode)assert(fail,timeLegend.includes('Рамка — свободный слот под логистику в день без съёмки'),
    'B008: домашняя легенда не объясняет пустую рамку');
  assert(fail,html.includes('i.log-empty{box-sizing:border-box;background:transparent;border:1.5px solid #F5F6F8}'),
    'B008: рамка пустого слота не использует точный цвет логистики/рабочих пауз');
  assert(fail,html.includes('.slg-note{font-style:normal;font-weight:400'),
    'B008: пояснения в скобках легенды не зафиксированы обычным начертанием');
  assert(fail,text(d.querySelector('[data-block-id="REPORT-B008"] .hint[data-t="rhi_09"]'))==='Структура вашей рабочей недели на основе введённых данных',
    'B008: изменён утверждённый подзаголовок календаря');
  /* Текст B006 ранее утверждён отдельно: календарная правка не должна
     самовольно переписывать его. */
  const logisticsBlock=text(d.querySelector('[data-block-id="REPORT-B006"]'));
  assert(fail,logisticsBlock.includes('Логистика в расчёт не входит')&&logisticsBlock.includes('относятся к личным расходам работника и не включаются в расчёт'),
    'B006: изменён утверждённый текст пояснения логистики');
  assert(fail,!d.querySelector('#logisticsNotice'),'B006: оставлен неутверждённый динамический текст');
  for(const label of ['Обработка','Продвижение','Работа с клиентом','Учёт','Рабочие паузы','Форс-мажоры','Управление']){
    assert(fail,timeLegend.includes(label),'B008: в легенде нет «'+label+'»');
    assert(fail,timeTable.includes(label),'B008: в таблице нет строки «'+label+'»');
  }
  /* Это инвариант любого набора входных данных, а не только default:
     съёмка всегда обрамлена двумя часами дороги. Без съёмки при аренде
     они стоят на 09:00/19:00, а дома превращаются лишь в пустые рамки.
     Заодно покрывается съёмка на границе базового интервала. */
  for(let day=0;day<5;day++){
    const shoots=[...Array(11)].map((_,row)=>9+row).filter(hour=>cellHas(hour,day,'Съёмка')),
          logistics=[...Array(11)].map((_,row)=>9+row).filter(hour=>wkCell(hour,day)?.title==='Логистика');
    if(shoots.length){
      assert(fail,logistics.length===2,'B008: в съёмочном дне нет двух часов логистики (день '+day+')');
      assert(fail,logistics.some(hour=>hour<shoots[0])&&logistics.some(hour=>hour>shoots[shoots.length-1]),
             'B008: логистика не обрамляет съёмку (день '+day+')');
    }else if(officeMode){
      assert(fail,logistics.length===2&&wkCell(9,day)?.title==='Логистика'&&wkCell(19,day)?.title==='Логистика',
             'B008: в дне арендуемого помещения нет логистики до/после рабочего дня (день '+day+')');
    }else{
      assert(fail,logistics.length===0,'B008: домашняя логистика показана в дне без съёмки (день '+day+')');
      assert(fail,wkCell(9,day)?.classList.contains('log-empty')&&wkCell(19,day)?.classList.contains('log-empty'),
             'B008: домашние пустые слоты не показаны серой рамкой (день '+day+')');
    }
  }
  assert(fail,text(d.querySelector('.wt-h'))==='Вот столько времени вы тратите на выполнение каждого вида работ:',
         'B008: не установлен утверждённый заголовок таблицы времени');
  assert(fail,!d.querySelector('#wkMgmtWarn')&&!text(d.body).includes('Время на управление не заложено'),
         'B008: оставлено удалённое предупреждение о нулевом управлении');
  /* На мобильном нижний отступ от плашки до заголовка равен фактическому
     верхнему отступу: позднее общее правило .wf-split даёт ему 48 px. */
  assert(fail,html.includes('#phr-root .wf-split{margin-top:48px}')&&
              html.includes('#phr-root #card02 .wt-h{margin-top:48px}'),
         'B008: на мобильном не уравнен отступ плашки до заголовка таблицы');
  if(injected){
    const allPerShoot=injected.sh>0
      ? (injected.sh+injected.post+injected.promo+injected.clT+injected.accT+injected.idle+(injected.fmT||0)+(injected.mgmtT||0))/injected.sh : 0;
    const rounded=Math.round(allPerShoot*10)/10;
    const expected=rounded.toLocaleString('ru-RU',{minimumFractionDigits:rounded%1?1:0,maximumFractionDigits:1}).replace(/\u00a0/g,' ');
    assert(fail,text(d.querySelector('#wfTot')).includes(expected),'B008: управление не входит в «Работы в целом»');
    if((injected.mgmtT||0)<=0.005){
      assert(fail,timeLegend.includes('Управление — 0 ч'),'B008: нулевое управление не подписано как 0 ч в легенде');
    } else {
      assert(fail,!timeLegend.includes('Управление — 0 ч'),'B008: ненулевое управление ошибочно подписано как 0 ч');
    }
    /* Продвижение — регулярная деятельность: при пяти и более часах в
       неделю оно не имеет права собраться в одном дне. */
    const promoDays=[];
    for(let day=0;day<5;day++){
      if([...Array(11)].some((_,row)=>cellHas(9+row,day,'Продвижение')))promoDays.push(day);
    }
    if(injected.promo/(injected.NW||43.8)>=5-0.005)
      assert(fail,promoDays.length===5,'B008: продвижение не распределено по всем рабочим дням');
    if(name==='default'||name==='min_shoot'){
      for(let day=0;day<5;day++){
        const shoots=[...Array(11)].map((_,row)=>9+row).filter(hour=>cellHas(hour,day,'Съёмка')),
              logistics=[...Array(11)].map((_,row)=>9+row).filter(hour=>wkCell(hour,day)?.title==='Логистика');
        if(shoots.length){
          assert(fail,shoots[0]===11,'B008: съёмочный день начинается не в 11:00');
          assert(fail,!shoots.includes(14),'B008: съёмка заняла обязательный обед');
          assert(fail,logistics.length===2,'B008: в съёмочном дне нет двух часов логистики');
          assert(fail,logistics.some(hour=>hour<shoots[0])&&logistics.some(hour=>hour>shoots[shoots.length-1]),
                 'B008: логистика не стоит до и после съёмки');
          assert(fail,!!wkCell(9,day)?.title&&!!wkCell(19,day)?.title,
                 'B008: работа не вынесена на 09:00 и 19:00 в съёмочный день');
        } else {
          assert(fail,logistics.length===0,'B008: логистика показана в домашнем дне без съёмки');
          assert(fail,!wkCell(9,day)?.title&&!wkCell(19,day)?.title,
                 'B008: пустые домашние слоты ошибочно стали работой');
          assert(fail,wkCell(9,day)?.classList.contains('log-empty')&&wkCell(19,day)?.classList.contains('log-empty'),
                 'B008: крайние слоты без съёмки не стали пустой серой рамкой');
          assert(fail,cellHas(10,day,'Продвижение'),'B008: утреннее продвижение пропало из дня без съёмки');
        }
        for(const hour of [14,17,18])
          assert(fail,!cellHas(hour,day,'Обработка')&&!cellHas(hour,day,'Клиент'),
                 'B008: гибкая работа заняла регулярный блок '+hour+':00');
      }
    }
    /* B030: у каждой роли без сектора сохраняются плашка и персонаж,
       но исчезают только выноска/точка; процент заменяет ссылка к её
       полю анкеты. Это общее правило, не только для управления. */
    const b030Roles=[
      /* Фигуры больше не меняются вслед за долей сектора: это принятые
         размеры DEMO-композиции. Управляющий слегка выше, чтобы при
         локте на кромке его подошвы естественно выступали ниже плашки. */
      {chip:0,hours:(injected.sh||0)+(injected.post||0),href:'calc.html#frm',go:'Заложить время на съёмку и обработку',name:'фотограф',growth:'2.759'},
      {chip:1,hours:injected.clT||0,href:'calc.html#c_FormClientTime',go:'Заложить время на работу с клиентами',name:'отдел продаж',growth:'1.627'},
      {chip:2,hours:injected.promo||0,href:'calc.html#c_FormPromoTime',go:'Заложить время на продвижение',name:'отдел маркетинга',growth:'2.036'},
      {chip:3,hours:injected.accT||0,href:'calc.html#c_Form011',go:'Заложить время на учёт',name:'бухгалтер',growth:'1.329'},
      {chip:4,hours:injected.mgmtT||0,href:'calc.html#c_FormMgmt',go:'Заложить время на управление',name:'управление',growth:'1.360'},
    ], b030Lines=d.querySelectorAll('#monFig .monfig-svg polyline'),
       b030Dots=d.querySelectorAll('#monFig .monfig-svg circle');
    b030Roles.forEach(role=>{
      const chip=d.querySelector('#monC'+role.chip), link=chip?.querySelector('.mon-zero-link'),
            zero=role.hours<=0.005;
      assert(fail,!!chip,'B030: нет плашки роли «'+role.name+'»');
      assert(fail,chip?.style.getPropertyValue('--рост').trim()===role.growth,
             'B030: размер персонажа «'+role.name+'» зависит от доли сектора или изменён');
      if(zero){
        assert(fail,chip?.classList.contains('mon-zero'),'B030: нулевая роль «'+role.name+'» не стала предупреждением');
        assert(fail,text(chip).includes('0 ₽/мес'),'B030: в предупреждении «'+role.name+'» нет 0 ₽/мес');
        assert(fail,!!chip?.querySelector('.mon-man'),'B030: персонаж нулевой роли «'+role.name+'» скрыт');
        assert(fail,!!link&&link.getAttribute('href')===role.href,'B030: ссылка нулевой роли «'+role.name+'» ведёт не к её полю');
        assert(fail,text(chip).includes(role.go),'B030: нет ссылки «'+role.go+'»');
        assert(fail,!text(chip).includes('от общего дохода'),'B030: процент остался в нулевой плашке «'+role.name+'»');
        assert(fail,b030Lines[role.chip]?.style.display==='none','B030: линия нулевой роли «'+role.name+'» не скрыта');
        assert(fail,b030Dots[role.chip]?.style.display==='none','B030: точка нулевой роли «'+role.name+'» не скрыта');
      } else {
        assert(fail,!chip?.classList.contains('mon-zero'),'B030: оплачиваемая роль «'+role.name+'» ошибочно стала предупреждением');
        assert(fail,!link,'B030: ссылка роли «'+role.name+'» показана при ненулевом секторе');
        assert(fail,text(chip).includes('от общего дохода'),'B030: в обычной плашке «'+role.name+'» пропал процент');
        assert(fail,b030Lines[role.chip]?.style.display!=='none','B030: линия ненулевой роли «'+role.name+'» скрыта');
        assert(fail,b030Dots[role.chip]?.style.display!=='none','B030: точка ненулевой роли «'+role.name+'» скрыта');
      }
    });
    assert(fail,html.includes('var ФИКС_РОСТ={0:2.759,1:1.627,2:2.036,3:1.329,4:1.360};')&&
                !html.includes('МИН_РОСТ+(МАКС_РОСТ-МИН_РОСТ)*(пц/100)'),
           'B030: не отключена зависимость масштаба персонажей от процента');
    assert(fail,html.includes('var эталонУгол=дист(прод.right,прод.bottom);')&&
                html.includes('var mk=бр.getBoundingClientRect();')&&
                html.includes('var left=mk.right+знак*dxМод;'),
           'B030: управляющий не привязан угловым расстоянием к продажам и маркетингу');
  }
  if(name==='min_shoot'){
    const plan=injected.projectPlan||{};
    assert(fail,Array.isArray(plan.projects)&&plan.projects.length>0,
           'B008: calc.html не передал сформированные целые проекты');
    assert(fail,(plan.projects||[]).every(project=>project.shoot+1e-8>=(plan.minShoot||0)),
           'B008: upstream-план содержит проект короче минимального заказа');
    assert(fail,(plan.projects||[]).every(project=>Number.isFinite(project.client)&&Number.isFinite(project.post)),
           'B008: у готового проекта отсутствует клиентское время или обработка');
    assert(fail,weekGrids.some((_,week)=>[...Array(5)].some((_,day)=>
      [...Array(11)].some((_,row)=>cellHas(9+row,day,'Обработка',week)))),
      'B008: обработка не заняла ни одного свободного окна');
  }
  if(name==='long_order'){
    const plan=injected.projectPlan||{}, allCells=[...d.querySelectorAll('#wk .wk-week i')];
    assert(fail,(plan.weeks||0)>1&&weekGrids.length===plan.weeks,
      'B008: длинный минимальный заказ не развёрнут в полный набор недель');
    assert(fail,d.querySelector('#wk')?.classList.contains('wk-plan'),
      'B008: длинный заказ не получил единый многонедельный календарь');
    assert(fail,allCells.filter(cell=>cell.title==='Обед').length===plan.weeks*5,
      'B008: в длинном календаре потеряны обязательные обеды');
    for(const role of ['Продвижение','Учёт','Управление','Рабочие паузы','Съёмка','Обработка','Работа с клиентом'])
      assert(fail,allCells.some(cell=>(cell.title||'').split(' · ').includes(role)),
        'B008: в длинном календаре потеряна обязательная роль «'+role+'»');
  }

  const inputSection=[...d.querySelectorAll('#спрдет .пункт[data-таб]')]
    .find(x=>text(x.querySelector('.шапка .имя')).includes('Вводные данные'));
  const inputText=text(inputSection);
  const marginRow=[...d.querySelectorAll('#спрдет tr')]
    .find(row=>text(row).includes('Запас выручки до точки безубыточности'));
  const investmentBanner=d.querySelector('#инвПлашка');
  if(injected){
    if((injected.profitY||0)>0){
      assert(fail,investmentBanner?.classList.contains('dnsum')&&investmentBanner?.classList.contains('res')&&investmentBanner?.classList.contains('inv-payback'),
             'B024: окупаемость не оформлена структурой баннера «Отложите в резерв»');
      const paybackTitle=investmentBanner?.querySelector('.dsh'),
            paybackValue=investmentBanner?.querySelector('.dsb'),
            paybackCopy=investmentBanner?.querySelector('.dsl');
      assert(fail,text(paybackTitle)==='Ваше вложение окупится за',
             'B024: в верхней строке баннера неверный текст срока');
      assert(fail,/^\d+(?:,\d+)?\s+(?:год|года|лет)$/.test(text(paybackValue)),
             'B024: срок не выведен центральным числовым показателем');
      assert(fail,!!investmentBanner?.querySelector('.dsdeco')&&!!paybackCopy,
             'B024: не повторены декор и разделитель баннера «Отложите в резерв»');
      assert(fail,text(paybackCopy)==='После возврата инвестиций вы сможете направить эти средства на развитие бизнеса или увеличить личный доход.',
             'B024: нет утверждённого пояснения после возврата инвестиций');
      assert(fail,!text(investmentBanner).includes('Считаем по чистой прибыли')&&!investmentBanner?.querySelector('.ip-s'),
             'B024: оставлена удалённая строка о чистой прибыли');
      assert(fail,html.includes('#phr-root #инвестиции{padding:22px 0 26px')&&
                  html.includes('#phr-root .invfig{position:relative;margin:26px 0 14px')&&
                  html.includes('#phr-root #инвПлашка.dnsum.res{margin:26px 0 0;border-radius:var(--r)}')&&
                  html.includes('#phr-root #инвПлашка.inv-payback-warn{margin:26px 0 0}'),
             'B024: сцена или баннер не растянуты на полную ширину блока без подложки либо не скруглён со всех сторон');
    }else{
      assert(fail,investmentBanner?.classList.contains('mp-sec')&&investmentBanner?.classList.contains('inv-payback-warn'),
             'B024: невозможная окупаемость не оформлена жёлтым уведомлением');
      assert(fail,text(investmentBanner).includes('Вложения не окупятся никогда'),
             'B024: в жёлтом уведомлении нет состояния «никогда»');
    }
  }
  if(name==='default'){
    assert(fail,text(marginRow).includes('Запас выручки до точки безубыточности'),
           'в детализации нет запаса выручки до точки безубыточности');
  }
  if(name==='loss'){
    assert(fail,text(marginRow).includes('−'),'запас выручки ниже точки безубыточности не показан знаком минус');
  }
  if(name==='zero_rate'){
    assert(fail,text(marginRow).includes('—'),'нулевая текущая ставка не показана как неопределённый запас');
  }
  if(name==='loss'){
    assert(fail,d.querySelector('#dns .loss')!==null,'нет визуализации убытка');
    assert(fail,text(d.querySelector('#dns')).includes('Убыток'),'нет подписи Убыток');
  }
  if(name==='tax_off')assert(fail,inputText.includes('Не учитывается'),'нет ответа «Не учитывается»');
  if(name==='funds')assert(fail,text(d.querySelector('#fnd')).length>50,'не отрисована программа лояльности');
  if(name==='site_self'){
    assert(fail,inputText.includes('Сколько времени вы потратили на создание сайта'),'нет времени самостоятельного сайта');
    assert(fail,!inputText.includes('Сколько вы заплатили за создание сайта'),'показана неактивная стоимость подрядчика');
  }
  if(name==='excluded'){
    for(const forbidden of ['Проектная работа с клиентами','Поиск заказов','Кто ведёт учёт','Кто делал сайт'])
      assert(fail,!inputText.includes(forbidden),'показан исключённый ответ: '+forbidden);
  }

  // Минимальная интерактивность: детализация и окно благодарности должны открываться.
  const top=d.querySelector('#спрдет .пункт[data-верх] .шапка');
  if(top){const before=top.closest('.пункт').className;top.click();await wait(20);
    assert(fail,top.closest('.пункт').className!==before,'детализация не реагирует на клик');}
  const thanks=d.querySelector('[data-thx="report-top"]'),modal=d.querySelector('#thxModal');
  if(thanks&&modal){const before=modal.className;thanks.click();await wait(30);
    assert(fail,modal.className!==before,'окно благодарности не открывается');}

  dom.window.close();
  return {name,errors:fail,tables:d.querySelectorAll?.('table').length||12};
}

(async()=>{
  const scenarios=[
    ['demo',null],
    ['default',{}],
    ['query',{}],
    ['loss',{поля:{current_rate:'1000'}}],
    ['zero_rate',{поля:{current_rate:'0'}}],
    ['tax_off',{поля:{tax_off:true}}],
    ['funds',{поля:{fund_on:true,fund_pct:'10',disc_on:true,disc_pct:'15'}}],
    /* Без доли чистой прибыли вложения не имеют источника возврата:
       B024 обязан показать штатное жёлтое уведомление «никогда». */
    ['no_profit',{поля:{fund_on:false}}],
    ['min_shoot',{поля:{shoot_manual:'2'}}],
    /* Минимальный полный заказ (12 ч съёмки + связанные часы) больше
       проектной ёмкости недели: все недели должны быть видны разом. */
    ['long_order',{поля:{shoot_manual:'12',mgmt_amt:'2',mgmt_per:'week'},EXC_ВНЕШ:{FormMgmt:false}}],
    /* Предельный календарный случай: 35 съёмочных часов в неделю,
       без постобработки и прочих скрытых задач. Он вынуждает съёмку
       занять границы базового дня и проверяет, что оба часа дороги
       всё равно остаются до/после неё. */
    ['edge_shoot',{поля:{shoot_manual:'8',post_ratio:'0'},EXC_ВНЕШ:{FormClientTime:true,FormPromoTime:true,Form011:true,FormMgmt:true,Form009b:true,Form015b:true}}],
    /* Арендуемое помещение: два часа дороги нужны даже в дне без съёмки,
       строго до старта и после окончания рабочего дня. */
    ['office_logistics',{радио:{ws_mode:'office'}}],
    ['management',{поля:{mgmt_amt:'2',mgmt_per:'week'},EXC_ВНЕШ:{FormMgmt:false}}],
    ['zero_client',{EXC_ВНЕШ:{FormClientTime:true}}],
    ['site_self',{радио:{site_mode:'self'}}],
    ['excluded',{EXC_ВНЕШ:{FormClientTime:true,FormPromoTime:true,Form009b:true,Form006:true,Form014:true,Form015b:true,Form011:true}}],
  ];
  let failed=[];
  for(const [name,override] of scenarios){
    const r=await render(name,override);
    if(r.errors.length)failed.push(...r.errors.map(x=>name+': '+x));
    else console.log('✓ '+name);
  }
  if(failed.length){console.error(failed.map(x=>'✗ '+x).join('\n'));process.exit(1)}
  console.log(`Headless report: ${scenarios.length} сценариев · 30 блоков · 13 таблиц · ошибок 0`);
})().catch(e=>{console.error(e.stack||e);process.exit(2)});
