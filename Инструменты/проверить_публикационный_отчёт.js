#!/usr/bin/env node
/* Проверяет публикационную сборку Публикация/report.html.

   Development report.html намеренно содержит DEMO для разработки. Публикационный
   файл собирается из него, но принимает только настоящий d; без ?data= и
   phc_report показывает единственный путь в calc.html.
*/
const fs=require('fs'),path=require('path'),cp=require('child_process');
let JSDOM,VirtualConsole;
try{({JSDOM,VirtualConsole}=require('jsdom'))}catch(e){
  console.error('Не установлен jsdom. Выполните npm ci в папке Инструменты.');process.exit(3);
}
const ROOT=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const REPORT=path.join(ROOT,'Веб','Публикация','report.html');
const BUILDER=path.join(ROOT,'Инструменты','собрать_публикационный_отчёт.py');
const BROWSER_DEFAULT=path.join(ROOT,'Инструменты','проверить_calc_browser_default.js');
function fail(message){throw Error('публикационный отчёт: '+message)}
function wait(ms){return new Promise(resolve=>setTimeout(resolve,ms))}
function browserDefault(){
  const result=cp.spawnSync('node',[BROWSER_DEFAULT,ROOT,'--assert','--result'],{encoding:'utf8'});
  if(result.status!==0)fail('browser-default: '+(result.stderr||result.stdout).trim().slice(0,300));
  const d=JSON.parse(result.stdout);d._ts=Date.now();return d;
}
async function render(name,data,throughQuery){
  const source=fs.readFileSync(REPORT,'utf8');
  const errors=[];let ignoredCss=0;
  const console=new VirtualConsole();
  console.on('jsdomError',error=>{
    if(error.message==='Could not parse CSS stylesheet')ignoredCss++;
    else errors.push(error.message);
  });
  console.on('error',error=>errors.push(String(error)));
  const query=data&&throughQuery
    ? '?data='+encodeURIComponent(Buffer.from(JSON.stringify(data),'utf8').toString('base64'))
    : '';
  const dom=new JSDOM(source,{url:'https://publication.schetiks.test/report.html'+query,
    runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:console,beforeParse(window){
      if(data&&!throughQuery)window.localStorage.setItem('phc_report',JSON.stringify(data));
      window.scrollTo=()=>{};
      window.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
      window.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};
      window.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
      if(!window.URL.createObjectURL)window.URL.createObjectURL=()=>'';
      if(!window.URL.revokeObjectURL)window.URL.revokeObjectURL=()=>{};
    }});
  await wait(700);
  const document=dom.window.document,root=document.getElementById('phr-root'),empty=document.getElementById('publication-empty');
  if(errors.length)fail(name+' — ошибки JS: '+errors.join(' | '));
  if(ignoredCss>1)fail(name+' — неожиданные ошибки CSS: '+ignoredCss);
  if(!root||!empty)fail(name+' — не найдены корень отчёта или пустое состояние');
  if(data){
    if(document.documentElement.classList.contains('phr-no-result'))fail(name+' — настоящий расчёт ошибочно скрыт');
    if(dom.window.PHR_D===null||dom.window.PHR_D.R!==data.R)fail(name+' — результат не передан в отчёт');
    if(root.hidden||root.style.display==='none'||dom.window.getComputedStyle(root).display==='none')fail(name+' — корень скрыт при настоящем расчёте');
    if(document.querySelector('#dns')?.textContent.replace(/\s+/g,' ').trim().length<=100)fail(name+' — не отрисованы сценарии');
  }else{
    if(!document.documentElement.classList.contains('phr-no-result'))fail('нет класса пустого состояния');
    if(dom.window.PHR_D!==null)fail('пустой отчёт получил подставные данные');
    if(!root.hidden&&dom.window.getComputedStyle(root).display!=='none')fail('без результата видна статическая разметка отчёта');
    if(dom.window.getComputedStyle(empty).display==='none')fail('не показано пустое состояние');
    const action=empty.querySelector('a[href="calc.html"]');
    if(!action||!action.textContent.includes('Заполнить анкету'))fail('нет пути обратно в анкету');
  }
  dom.window.close();
}
(async()=>{
  const built=cp.spawnSync('python3',[BUILDER,'--check'],{encoding:'utf8'});
  if(built.status!==0)fail((built.stderr||built.stdout).trim());
  if(!fs.existsSync(REPORT))fail('нет Веб/Публикация/report.html');
  const source=fs.readFileSync(REPORT,'utf8');
  if(/\bvar\s+DEMO\s*=/.test(source)||source.includes('return DEMO;'))
    fail('в публикационной копии остался исполняемый DEMO-набор');
  if(!source.includes('publication-empty')||!source.includes('phr-no-result'))
    fail('в публикационной копии нет защиты от прямого открытия');
  const d=browserDefault();
  await render('без данных',null,false);
  await render('localStorage',d,false);
  await render('?data=',d,true);
  console.log('Публикационный отчёт: 3 сценария · DEMO отсутствует · ошибок 0');
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
