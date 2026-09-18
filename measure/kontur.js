const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
const URL=process.argv[2]||'http://127.0.0.1:8001/calc.html';
/* Набирает контрольные точки раскладки, чтобы сравнить страницу ДО и ПОСЛЕ
   добавления <!DOCTYPE> (режим quirks -> standards может сдвинуть геометрию). */
const МЕТРИКИ=`(()=>{
  const g=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();
    return {w:Math.round(r.width),h:Math.round(r.height),top:Math.round(r.top+scrollY),left:Math.round(r.left)};};
  const cs=s=>{const e=document.querySelector(s);return e?getComputedStyle(e):null};
  const out={режим:document.compatMode,
    высотаСтраницы:document.documentElement.scrollHeight,
    h1:g('#phc-root h1'), hero:g('#phc-root .hero-cover'), heroCopy:g('#phc-root .hero-copy'),
    рядПлашек:g('#phc-root .benefits-grid'), плашка1:g('#phc-root .benefit'),
    хвост:g('#phc-root .benefits-tail'), хвостЗаголовок:g('#phc-root .start-note-title'),
    карточка01:g('#phc-root .card'), поле01:g('#phc-root input'),
    hint01:g('#phc-root .hint'), stepper:g('#phc-root .stepper button'),
    кнопкаРасчёта:g('#phc-root .btn'), плашкаИтога:g('#phc-root .income-card'),
    секцияВремя:g('#phc-root .form-section-time'),
    плашка06:g('#phc-root .card[data-block-id="CALC-B012"]'),
    bodyMargin:cs('body')?getComputedStyle(document.body).margin:null,
    lineHeight:cs('#phc-root')?getComputedStyle(document.querySelector('#phc-root')).lineHeight:null,
    скроллX:document.documentElement.scrollWidth,
    таб:document.title};
  /* сколько строк занимает подзаголовок 06 и где его маркировка */
  const p=document.querySelector('#phc-root .card[data-block-id="CALC-B012"] .post-subtitle');
  if(p){const r=document.createRange();r.selectNodeContents(p);
    const строки=[...r.getClientRects()].filter(x=>x.height>0);
    out.строкПодзаголовка06=строки.length;
    out.высотаПодзаголовка06=Math.round(p.getBoundingClientRect().height);}
  return out;})()`;
(async()=>{
  const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',
    args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
  const page=await b.newPage();
  for(const [имя,w] of [['десктоп',1440],['мобильный',390]]){
    await page.setViewport({width:w,height:1200,deviceScaleFactor:1});
    await page.goto(URL,{waitUntil:'networkidle0',timeout:60000});
    await new Promise(r=>setTimeout(r,700));
    console.log('###',имя);
    console.log(JSON.stringify(await page.evaluate(МЕТРИКИ),null,1));
  }
  await b.close();
})();
