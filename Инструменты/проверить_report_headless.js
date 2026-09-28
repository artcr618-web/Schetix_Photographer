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
        expectedWeeks=Math.max(1,Math.round(injected?.projectPlan?.weeks||weekGrids.length||1)),
        B008_START=8, B008_SLOTS=11;
  /* Каждая компактная неделя: заголовок + 11 строк 08:00–19:00. */
  assert(fail,weekGrids.length===expectedWeeks,
    'B008: число видимых недель не совпадает с готовым планом calc.html');
  assert(fail,(expectedWeeks>1)===d.querySelector('#wk')?.classList.contains('wk-plan'),
    'B008: класс многонедельного календаря не соответствует плану');
  assert(fail,weekGrids.every(grid=>grid.children.length===73),
    'B008: хотя бы одна неделя не содержит 11 часовых строк и нижнюю отметку 19:00');
  assert(fail,weekGrids.every(grid=>[...grid.children].at(-1)?.textContent==='19:00'),
    'B008: нижняя отметка календаря должна быть 19:00');
  /* На планшете первый столбец сужен до 42px. Конечная отметка 19:00
     абсолютна, поэтому её ширина обязана повторять ширину шкалы, иначе
     цифры съезжают вправо относительно 18:00 и остальных часов. */
  assert(fail,html.includes('#phr-root .wk-week{grid-template-columns:42px repeat(5,1fr)}\n#phr-root .wk-week .hr-end{width:42px}'),
    'B008: ширина нижней отметки 19:00 расходится со столбцом шкалы');
  function wkCell(hour,day,week=0){
    const cells=weekGrids[week]?[...weekGrids[week].children]:[];
    return cells[6+(hour-B008_START)*6+1+day]?.querySelector('i');
  }
  function cellLabel(hour,day,week=0){return wkCell(hour,day,week)?.getAttribute('aria-label')||''}
  function cellParts(hour,day,week=0){return cellLabel(hour,day,week).split(' · ').filter(Boolean)}
  function cellHas(hour,day,label,week=0){
    return cellParts(hour,day,week).some(part=>part===label||part.startsWith(label+','));
  }
  function partMinutes(part,label){
    if(part===label)return 60;
    const match=part.match(new RegExp('^'+label+',\\s*(\\d+)\\s*мин$'));
    return match?Number(match[1]):0;
  }
  function roleMinutes(day,label,week=0){return hours().reduce((total,hour)=>
    total+cellParts(hour,day,week).reduce((sum,part)=>sum+partMinutes(part,label),0),0)}
  function dataRoleHours(key){return [...d.querySelectorAll('#wk [data-b008-parts]')].reduce((total,cell)=>
    total+cell.dataset.b008Parts.split(',').reduce((sum,part)=>{
      const [partKey,value]=part.split(':');return sum+(partKey===key?Number(value):0);
    },0),0)}
  function dataRoleHoursDay(day,key,week=0){return hours().reduce((total,hour)=>{
    const raw=wkCell(hour,day,week)?.dataset.b008Parts||'';
    return total+raw.split(',').reduce((sum,part)=>{
      const [partKey,value]=part.split(':');return sum+(partKey===key?Number(value):0);
    },0);
  },0)}
  function hours(){return [...Array(B008_SLOTS)].map((_,row)=>B008_START+row)}
  function roleHours(day,label,week=0){return hours().filter(hour=>cellHas(hour,day,label,week))}
  /* B008 не использует native title: доступное название остаётся в aria-label,
     поэтому календарь не показывает запрещённые hover-подсказки. */
  assert(fail,[...d.querySelectorAll('#wk i')].every(cell=>!cell.hasAttribute('title')),
    'B008: в ячейки вернулся native title/hover');
  assert(fail,!d.querySelector('#wk .empty-dash'),
    'B008: в свободные ячейки вернулся прочерк вместо пустого пространства');
  assert(fail,html.includes('#phr-root .wk i.free,#phr-root .wk i.offshift{background:transparent;border:0}'),
    'B008: пустые либо нерабочие ячейки получили заливку или рамку');
  assert(fail,html.includes('linear-gradient(to right,'),
    'B008: состав часа рисуется не слева направо');
  const pauseIcons=d.querySelectorAll('#wk .pauseico, #wk .pausepartico');
  assert(fail,d.querySelector('#wklg .pauselegend .pauseico')!==null&&
    (!d.querySelector('[data-b008-parts*="id:"]')||pauseIcons.length>0),
    'B008: у размещённых рабочих пауз нет утверждённой иконки');
  for(const klass of ['pencilico','promoico','contactico','calculatorico','briefcaseico','forceico'])
    assert(fail,d.querySelector('#wklg .'+klass)!==null,
      'B008: иконка '+klass+' исчезла из обязательной легенды');
  assert(fail,html.includes("var ЛОГ_ЧАСТЬ={key:'log',c:'#FFFFFF',n:'Логистика',service:true};")&&
    html.includes('#phr-root .wk i.service .wkico.logico{width:24px;height:24px}')&&
    html.includes('#phr-root .wk i .shoot-label .camico{position:static;flex:none;width:24px;height:24px;')&&
    html.includes('#phr-root .wk i .pause-label .pauseico{position:static;flex:none;width:24px;height:24px')&&
    html.includes('#phr-root .wk i .wkpartico{position:absolute;z-index:2;left:var(--seg-center);top:50%;\nwidth:20px;height:20px;transform:translate(-50%,-50%);pointer-events:none}')&&
    html.includes('#phr-root .wk i .wkpartico.logico{color:var(--c-gr3)}')&&
    html.includes('#phr-root .wk i .wkpartico.forceico{color:#fff}')&&
    html.includes('#phr-root .wk i.service-partial{box-sizing:border-box}')&&
    html.includes('#phr-root .wk i .wklogpart{position:absolute;z-index:1;left:var(--seg-left);top:0;\nwidth:var(--seg-width);height:100%;box-sizing:border-box;border:1.5px solid var(--c-pause);')&&
    !html.includes('service-partial{box-sizing:border-box;box-shadow'),
    'B008: логистика перестала быть белой, её контур утолщился либо рамка смешанной ячейки задела соседнюю роль');
  const dividedShoot=[...d.querySelectorAll('#wk [data-b008-parts]')]
    .some(cell=>cell.dataset.b008Parts.includes('sh:')&&cell.dataset.b008Parts.includes('log:'));
  assert(fail,!dividedShoot||(d.querySelectorAll('#wk .wkpartico.camico').length>0&&d.querySelectorAll('#wk .wkpartico.logico').length>0),
    'B008: в разделённых половинах съёмки и логистики нет своих иконок');
  const partialService=[...d.querySelectorAll('#wk .service-partial')];
  assert(fail,partialService.every(cell=>{
    const logCount=cell.dataset.b008Parts.split(',').filter(part=>part.startsWith('log:')).length;
    return logCount===1&&cell.querySelectorAll('.wklogpart').length===logCount&&
      cell.querySelector('.wklogpart')?.style.getPropertyValue('--seg-width').endsWith('%');
  }),
    'B008: тонкий контур неполной логистики отсутствует либо затронул не-логистический сегмент');
  const fullRoleCells=[...d.querySelectorAll('#wk [data-b008-parts]')].filter(cell=>{
    const parts=cell.dataset.b008Parts.split(','),keys=parts.map(part=>part.split(':')[0]);
    return keys.length===1&&keys[0]!=='sh'&&Number(parts[0].split(':')[1])>=1-1e-6;
  });
  assert(fail,fullRoleCells.every(cell=>cell.querySelector('.wtxt')!==null&&
    cell.querySelector('.wtxt .roleico,.wtxt .pauseico')===null&&
    cell.querySelector('.wmb .roleico,.wmb .pauseico')!==null),
    'B008: в полной роли на десктопе осталась иконка рядом с подписью либо нет мобильной иконки');
  assert(fail,html.includes('@media(max-width:900px){\n#phr-root .wk i .wtxt{display:none}')&&
    html.includes('@media(max-width:900px){\n#phr-root .wk i .wmb{display:flex}}')&&
    html.includes("--seg-width:'+width+'%")&&html.includes('cellWidth*share/100>=28'),
    'B008: на планшете не включился режим иконки полной ячейки либо крупные сегменты лишены адаптивного знака');
  assert(fail,![...d.querySelectorAll('#wk [data-b008-parts]')].filter(cell=>cell.dataset.b008Parts.includes(',')).some(cell=>
    !cell.querySelector('.wkpartico')),
    'B008: в разделённой ячейке на десктопе не осталось иконки сегмента');
  for(const cell of d.querySelectorAll('#wk [data-b008-parts]')){
    const keys=cell.dataset.b008Parts.split(',').map(part=>part.split(':')[0]),
          pair=keys.slice().sort().join('+');
    assert(fail,['log+sh','log+po','fm+po','id+po'].includes(pair)||keys.length<2,
      'B008: разрешены только пары «съёмка+логистика», «логистика+обработка», «форс-мажор+обработка» и «обработка+пауза»: '+keys.join('+'));
    assert(fail,!(keys.includes('id')&&keys.includes('log'))&&!(keys.includes('id')&&keys.includes('fm')),
      'B008: рабочая пауза закрыла логистику или форс-мажор вместо обработки: '+keys.join('+'));
  }
  for(let week=0;week<weekGrids.length;week++)for(let day=0;day<5;day++){
    const lunches=hours().filter(hour=>cellLabel(hour,day,week)==='Обед'),
          shoots=roleHours(day,'Съёмка',week),
          partialShoots=hours().filter(hour=>cellHas(hour,day,'Съёмка',week)&&cellHas(hour,day,'Логистика',week)),
          logistics=roleHours(day,'Логистика',week);
    assert(fail,lunches.length===1,'B008: в дне нет ровно одного обязательного обеда');
    assert(fail,dataRoleHoursDay(day,'id',week)<=1+1e-6,
      'B008: в одном дне стало больше 1 часа рабочих пауз (день '+day+')');
    assert(fail,roleHours(day,'Рабочие паузы',week).every(hour=>hour>=13),
      'B008: рабочая пауза поставлена в начало дня или до обеда (день '+day+')');
    assert(fail,lunches.every(hour=>!cellHas(hour,day,'Съёмка',week)),
      'B008: съёмка заняла обязательный обед');
    partialShoots.forEach(hour=>assert(fail,cellHas(hour+1,day,'Логистика',week),
      'B008: после дробной точной съёмки нет непрерывного полного часа логистики'));
    if(shoots.length){
      assert(fail,roleMinutes(day,'Логистика',week)===120,
        'B008: на один съёмочный проект не зарезервированы ровно два часа логистики (день '+day+')');
      assert(fail,logistics.some(hour=>hour<shoots[0])&&logistics.some(hour=>hour>=shoots[shoots.length-1]),
        'B008: логистика не обрамляет съёмку (день '+day+')');
    }else{
      assert(fail,wkCell(17,day,week)?.classList.contains('offshift')&&wkCell(18,day,week)?.classList.contains('offshift'),
        'B008: день без съёмки не заканчивается после 8 рабочих часов и обеда (день '+day+')');
      assert(fail,roleMinutes(day,'Логистика',week)===0,
        'B008: в дне без съёмки добавлена несуществующая логистика (день '+day+')');
    }
  }
  const legendTitle=d.querySelector('#card02 .slg-h');
  assert(fail,text(legendTitle)==='Условные обозначения',
    'B008: над легендой нет заголовка «Условные обозначения»');
  const legendHeads=[...d.querySelectorAll('#wklg .slg-t')],
        hiddenHead=legendHeads.find(x=>text(x)==='Скрытая работа'),
        unpaidHead=legendHeads.find(x=>text(x)==='Неоплаченное время'),
        hiddenNote=hiddenHead?.parentElement.querySelector('.slg-note'),
        unpaidNote=unpaidHead?.parentElement.querySelector('.slg-note');
  assert(fail,!!hiddenHead&&!!unpaidHead&&hiddenNote?.tagName==='SPAN'&&unpaidNote?.tagName==='SPAN',
    'B008: нарушена иерархия групп условных обозначений');
  for(const label of ['Обед','Логистика','Обработка','Продвижение','Работа с клиентом','Учёт','Рабочие паузы','Форс-мажоры','Управление'])
    assert(fail,timeLegend.includes(label),'B008: в легенде нет «'+label+'»');
  /* Обед и логистика — визуальные неоплачиваемые сервисные слоты, не строки
     расчётной таблицы; остальные роли в таблице обязательны. */
  for(const label of ['Обработка','Продвижение','Работа с клиентом','Учёт','Рабочие паузы','Форс-мажоры','Управление','Съёмочных часов','Съёмочных проектов'])
    assert(fail,timeTable.includes(label),'B008: в таблице нет строки «'+label+'»');
  assert(fail,text(timeRows[0]).startsWith('Съёмочных часов')&&text(timeRows[1]).startsWith('Съёмочных проектов'),
    'B008: строки съёмочных часов и проектов стоят не в начале таблицы');
  const projectCells=[...timeRows[1].querySelectorAll('td')].map(text);
  assert(fail,projectCells.length===5&&projectCells[1]==='—'&&!/[,.]\d/.test(projectCells.slice(2).join(' ')),
    'B008: проекты за час не стали прочерком либо в периодах остались десятые');
  const hiddenRoleLegend=[...d.querySelectorAll('#wklg .rolelegend')];
  assert(fail,hiddenRoleLegend.length===7&&hiddenRoleLegend.every(icon=>
    /^#[0-9A-F]{6}$/i.test(icon.style.getPropertyValue('--legend-bg')))&&
    d.querySelector('#wklg .rolelegend .forceico')!==null,
    'B008: у каждой роли «Скрытой работы» нет собственной цветной подложки либо исчез белый зонтик');
  assert(fail,html.includes('#phr-root #card02 .slg i.slg-service-icon.rolelegend{box-sizing:border-box;background:var(--legend-bg);border:0;border-radius:6px}')&&
    html.includes('#phr-root #card02 .slg i.slg-service-icon.rolelegend .roleico{display:block;width:17px;height:17px;color:var(--c-gr3);--role-cut:var(--legend-bg)}')&&
    html.includes('#phr-root #card02 .slg i.slg-service-icon.rolelegend .forceico{color:#fff}'),
    'B008: в легенде скрытой работы вернулась рамка вместо подложки роли либо зонтик не белый');
  assert(fail,html.includes("var ИКОНКА_РОЛИ={po:ИКОНКА_ОБРАБОТКА,pr:ИКОНКА_ПРОДВИЖЕНИЕ,cl:ИКОНКА_КЛИЕНТ,ac:ИКОНКА_УЧЁТ,mg:ИКОНКА_УПРАВЛЕНИЕ,fm:ИКОНКА_ФОРС_МАЖОР,id:ИКОНКА_ПАУЗА};")&&
    html.includes('M5.1 19.6l1.55-5.05')&&html.includes('fill="currentColor"')&&html.includes('var(--role-cut,#D8EEDF)')&&
    html.includes('briefcaseico')&&html.includes('contactico')&&html.includes('calculatorico')&&html.includes('promoico')&&html.includes('forceico')&&
    /* «Продвижение»: меньшие полные стойки на общей нижней линии; клиент —
       компактное залитое сообщение, учёт — экран и четыре отдельные клавиши. */
    html.includes('x="4" y="19" width="16" height="2.5"')&&html.includes('x="5.8" y="14" width="3.25" height="5"')&&html.includes('x="14.96" y="5" width="3.25" height="14"')&&
    html.includes('transform="translate(2.7 2.8) scale(.76)"')&&html.includes('M5.2 4.2h13.6')&&html.includes('cx="8.8" cy="9.8"')&&
    html.includes('x="6.25" y="5.1" width="11.5" height="3.1"')&&html.includes('x="7" y="10.65" width="3.45" height="3.45"')&&html.includes('x="13.55" y="15.2" width="3.45" height="3.45"')&&
    html.includes('#phr-root .wk i .wkpartico.rolepartico{color:var(--c-gr3)}')&&
    html.includes('#phr-root .wk i .wkpartico.camico{color:#fff}')&&
    html.includes('#phr-root .wk i .wmb .roleico,#phr-root .wk i .wmb .pauseico,#phr-root .wk i .wmb .camico{display:block;flex:none;width:24px;height:24px}')&&
    html.includes('function подогнатьЗнакиСегментов()')&&html.includes('cellWidth*share/100>=28'),
    'B008: нарушены правила значков для целых и разделённых календарных ячеек');
  assert(fail,html.includes('#phr-root .wk i:not(.free):hover{filter:none;box-shadow:none}'),
    'B008: при наведении на ячейку вернулась лишняя обводка или подсветка');
  assert(fail,!html.includes('<rect x="3.5" y="3" width="17" height="18" rx="3.1"')&&!html.includes('M17.5 7.3v4.2M15.4 9.4h4.2'),
    'B008: иконка клиента всё ещё нарисована карточкой или с плюсом');
  assert(fail,text(d.querySelector('[data-block-id="REPORT-B008"] .hint[data-t="rhi_09"]'))==='Структура вашей рабочей недели на основе введённых данных',
    'B008: изменён утверждённый подзаголовок календаря');
  assert(fail,text(d.querySelector('.wt-h'))==='Вот столько времени вы тратите на выполнение каждого вида работ:',
    'B008: не установлен утверждённый заголовок таблицы времени');
  if(injected){
    const allPerShoot=injected.sh>0
      ? (injected.sh+injected.post+injected.promo+injected.clT+injected.accT+injected.idle+(injected.fmT||0)+(injected.mgmtT||0))/injected.sh : 0;
    const rounded=Math.round(allPerShoot*10)/10;
    const expected=rounded.toLocaleString('ru-RU',{minimumFractionDigits:rounded%1?1:0,maximumFractionDigits:1}).replace(/\u00a0/g,' ');
    assert(fail,text(d.querySelector('#wfTot')).includes(expected),'B008: управление не входит в «Работы в целом»');
    const regular=injected.projectPlan?.regular||{}, dailyPromo=(regular.promo||0)/Math.max(1,(injected.projectPlan?.weeks||1)*5);
    /* Для целой дневной нормы каждый день содержит весь объём продвижения.
       Это защищает 2 ч/день по умолчанию от возврата недельного «хвоста». */
    if((name==='default'||name==='query'||name==='management'||name==='management5')&&Math.abs(dailyPromo-Math.round(dailyPromo))<1e-8){
      for(let week=0;week<weekGrids.length;week++)for(let day=0;day<5;day++)
        assert(fail,roleHours(day,'Продвижение',week).length===Math.round(dailyPromo),
          'B008: продвижение не размещено полной дневной нормой (неделя '+(week+1)+', день '+day+')');
    }
    if(name==='default'||name==='query'){
      assert(fail,projectCells.join(' | ')==='Съёмочных проектов | — | 4 проекта | 14 проектов | 175 проектов',
        'B008: DEMO-проекты считаются не по дискретному плану 4 / 14 / 175');
      for(let day=0;day<5;day++)for(let hour=8;hour<18;hour++)
        assert(fail,!wkCell(hour,day)?.classList.contains('free'),
          'B008: в DEMO осталась пустая ячейка внутри рабочего дня ('+hour+':00, день '+day+')');
      assert(fail,[0,1,2,3,4].every(day=>dataRoleHoursDay(day,'id')<=1+1e-6),
        'B008: стандартный план превысил лимит 1 ч рабочих пауз в день');
      const forceDays=[0,1,2,3,4].filter(day=>roleHours(day,'Форс-мажоры').length);
      assert(fail,forceDays.length===1&&roleHours(forceDays[0],'Форс-мажоры').every((hour,index,list)=>!index||hour===list[index-1]+1),
        'B008: форс-мажор не собран одним последовательным блоком');
      const ownPostTails=[...d.querySelectorAll('#wk [data-b008-parts]')].filter(cell=>{
        const parts=cell.dataset.b008Parts.split(',');
        return parts.some(part=>part.startsWith('po:')&&Number(part.slice(3))<1-1e-6)&&
          !parts.some(part=>part.startsWith('log:')||part.startsWith('fm:'));
      });
      assert(fail,ownPostTails.length===0,
        'B008: после закрытия точных хвостов обработка оставила лишнюю дробную ячейку');
      assert(fail,[0,1,2,3,4].every(day=>Math.abs(dataRoleHoursDay(day,'id')-1)<1e-6),
        'B008: после сборки точных хвостов не получился полный час паузы в каждом дне');
      assert(fail,d.querySelector('#wkShort')?.hidden,
        'B008: обработка не закрыла точный остаток форс-мажора и создала ложный дефицит');
      const fmPostCells=[...d.querySelectorAll('#wk [data-b008-parts]')].filter(cell=>
        cell.dataset.b008Parts.includes('fm:')&&cell.dataset.b008Parts.includes('po:'));
      assert(fail,fmPostCells.length===1,
        'B008: дробный остаток форс-мажора не закрыт обработкой');
    }
    if(name==='default'||name==='query'||name==='management'){
      assert(fail,roleHours(0,'Управление').length===2&&[1,2,3,4].every(day=>roleHours(day,'Управление').length===0),
        'B008: 2 ч управления в неделю должны быть единым блоком в понедельник');
      assert(fail,[0,1,2,3,4].every(day=>{
        const eveningStart=roleHours(day,'Съёмка').length?17:16;
        return roleHours(day,'Продвижение').some(hour=>hour>=eveningStart);
      }), 'B008: в каждом рабочем дне должна быть вечерняя полоса продвижения в доступной ёмкости дня');
    }
    assert(fail,!html.includes('Math.ceil(raw*2-1e-8)/2'),
      'B008: календарь округляет точную длительность съёмки');
    if(name==='default'||name==='query')assert(fail,
      Math.abs(dataRoleHours('sh')-(injected.projectPlan?.totals?.shoot||0))<1e-5,
      'B008: календарь потерял точную длительность съёмки в обычном плане');
    if(name==='management5'){
      assert(fail,[2,2,1,0,0].every((count,day)=>roleHours(day,'Управление').length===count),
        'B008: 5 ч управления должны распределиться блоками ПН 2 ч, ВТ 2 ч, СР 1 ч');
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
    assert(fail,html.includes('var Gпрод=тр?зазор(тр):эталон;')&&
                html.includes('var Gф=зазор(лм);')&&
                html.includes('function между(a,b){'),
           'B030: управляющий не привязан угловым расстоянием к продажам и маркетингу');
    /* 28.09: в мобильном одноколоночном строю управление находится
       непосредственно над продажами. Управляющий остаётся справа:
       алгоритм мобильных групп не вправе возвращать его к общему левому краю. */
    assert(fail,/\.cam-chip\.p-mg\{order:5\}[\s\S]*?\.cam-chip\.p-tr\{order:6\}/.test(html),
           'B030: в мобильном строю «Как управляющий» не стоит непосредственно над отделом продаж');
    assert(fail,/\.p-mg \.mon-man\{left:100%;\s*right:auto;[\s\S]*?top:calc\(var\(--H-чел\) \* -0\.304\)[\s\S]*?margin-left:calc\(var\(--H-чел\) \* -0\.291\)/.test(html),
           'B030: управляющий утратил правую посадку локтем на верхней кромке');
    assert(fail,html.includes("if(c.classList.contains('p-mg')) return;")&&
                html.includes("if(c.classList.contains('p-mg')) h=hПл*1.60;")&&
                html.includes('var управ=поле.querySelector(\'.p-mg\'), вылетУпр=0;')&&
                html.includes('управ.style.width=Math.max(80,W-вылетУпр).toFixed(1)+\'px\';'),
           'B030: мобильная раскладка не увеличивает или не укорачивает группу управляющего по её правому краю');
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
      [...Array(11)].some((_,row)=>cellHas(B008_START+row,day,'Обработка',week)))),
      'B008: обработка не заняла ни одного свободного окна');
  }
  if(name==='long_order'){
    const plan=injected.projectPlan||{}, allCells=[...d.querySelectorAll('#wk .wk-week i')];
    assert(fail,(plan.weeks||0)>1&&weekGrids.length===plan.weeks,
      'B008: длинный минимальный заказ не развёрнут в полный набор недель');
    assert(fail,d.querySelector('#wk')?.classList.contains('wk-plan'),
      'B008: длинный заказ не получил единый многонедельный календарь');
    assert(fail,allCells.filter(cell=>cell.getAttribute('aria-label')==='Обед').length===plan.weeks*5,
      'B008: в длинном календаре потеряны обязательные обеды');
    /* Роли могут делить один неполный слот, который намеренно не выводит
       несколько названий; их наличие уже подтверждено легендой и таблицей,
       поэтому здесь проверяем именно разворачивание календарного горизонта. */
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
      assert(fail,text(paybackTitle)==='Ваши вложения окупятся за',
             'B024: в верхней строке баннера неверный текст срока');
      assert(fail,/^\d+(?:,\d+)?\s+(?:год|года|лет)(?:\s+и\s+\d+\s+месяц(?:а|ев)?)?$/.test(text(paybackValue)),
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
    /* Режим рабочего места не создаёт фиктивную дорогу: два логистических
       часа принадлежат съёмочному проекту, а не каждому календарному дню. */
    ['office_logistics',{радио:{ws_mode:'office'}}],
    ['management',{поля:{mgmt_amt:'2',mgmt_per:'week'},EXC_ВНЕШ:{FormMgmt:false}}],
    ['management5',{поля:{mgmt_amt:'5',mgmt_per:'week'},EXC_ВНЕШ:{FormMgmt:false}}],
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
