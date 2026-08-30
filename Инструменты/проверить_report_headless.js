#!/usr/bin/env node
/* Постоянная jsdom-проверка настоящего report.html по нескольким сценариям. */
const fs=require('fs'), path=require('path'), cp=require('child_process');
let JSDOM,VirtualConsole;
try{({JSDOM,VirtualConsole}=require('jsdom'))}catch(e){
  console.error('Не установлен jsdom. Выполните npm ci в корне проекта.');process.exit(3);
}
const ROOT=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const REPORT=path.join(ROOT,'Веб','report.html');
const HARNESS=path.join(ROOT,'Инструменты','харнесс.js');
const html=fs.readFileSync(REPORT,'utf8');

function calculation(override){
  const p=cp.spawnSync('node',[HARNESS,ROOT,JSON.stringify(override||{})],{encoding:'utf8'});
  if(p.status!==0)throw Error('харнесс: '+(p.stderr||p.stdout).trim().slice(0,300));
  const d=JSON.parse(p.stdout);delete d.__parts;d._ts=Date.now();return d;
}
function assert(list,cond,msg){if(!cond)list.push(msg)}
function text(el){return el?el.textContent.replace(/\s+/g,' ').trim():''}
function wait(ms){return new Promise(r=>setTimeout(r,ms))}

async function render(name,override){
  const errors=[],vc=new VirtualConsole();let ignoredPageMarginCss=0;
  vc.on('jsdomError',e=>{if(e.message==='Could not parse CSS stylesheet')ignoredPageMarginCss++;else errors.push(e.message)});vc.on('error',e=>errors.push(String(e)));
  const injected=override===null?null:calculation(override);
  const dom=new JSDOM(html,{url:'https://schetix.test/report.html'+(injected?'':'?demo=1'),
    runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
      if(injected)w.localStorage.setItem('phc_report',JSON.stringify(injected));
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
  assert(fail,ids.length===20&&new Set(ids).size===20,'не 20 уникальных блоков');
  assert(fail,d.querySelector('.wp')?.children.length===20,'не 20 прямых блоков .wp');
  assert(fail,text(d.querySelector('#dns')).length>100,'не отрисованы три сценария');
  assert(fail,d.querySelectorAll('table').length===12,'ожидалось 12 таблиц');
  assert(fail,d.querySelectorAll('table tbody tr').length>=150,'меньше 150 строк таблиц');
  assert(fail,text(d.querySelector('#спрдет')).length>20000,'не собрана детализация/справочник');
  assert(fail,d.querySelector('#dn1 svg')!==null,'не построена диаграмма бюджета');
  assert(fail,d.querySelector('#wk')?.children.length>0,'не построен недельный график');

  const inputSection=[...d.querySelectorAll('#спрдет .пункт[data-таб]')]
    .find(x=>text(x.querySelector('.шапка .имя')).includes('Вводные данные'));
  const inputText=text(inputSection);
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
    ['loss',{поля:{current_rate:'1000'}}],
    ['zero_rate',{поля:{current_rate:'0'}}],
    ['tax_off',{поля:{tax_off:true}}],
    ['funds',{поля:{fund_on:true,fund_pct:'10',disc_on:true,disc_pct:'15'}}],
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
  console.log(`Headless report: ${scenarios.length} сценариев · 20 блоков · 12 таблиц · ошибок 0`);
})().catch(e=>{console.error(e.stack||e);process.exit(2)});
