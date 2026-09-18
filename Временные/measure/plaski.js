const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
for(const w of [1440,1280,1180,1024,768,390]){
 await page.setViewport({width:w,height:1000,deviceScaleFactor:1});
 await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
 await new Promise(r=>setTimeout(r,450));
 const m=await page.evaluate(()=>[...document.querySelectorAll('#phc-root .benefit')].map(c=>{
  const ic=c.querySelector('.benefit-icon'),t=c.querySelector('.benefit-title');
  const ir=ic.getBoundingClientRect(),tr=t.getBoundingClientRect();
  const r=document.createRange();r.selectNodeContents(t);
  const строки=[...r.getClientRects()].filter(x=>x.height>0);
  return {заг:t.textContent.replace(/\s+/g,' ').trim().slice(0,24),
   строк:строки.length,
   иконка_низ:Math.round(ir.bottom),
   текст_верх:Math.round(строки[0].top),
   зазор_иконка_текст:Math.round(строки[0].top-ir.bottom),
   черта:Math.round(tr.bottom),
   текста_до_черты:Math.round(tr.bottom-(строки[строки.length-1].bottom)),
   плашка:Math.round(c.getBoundingClientRect().height)}}));
 console.log('### ширина',w);m.forEach(x=>console.log('  ',JSON.stringify(x)));
}
await b.close();})();
