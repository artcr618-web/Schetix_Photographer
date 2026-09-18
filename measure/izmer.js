const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');

(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',
  args:['--no-sandbox','--disable-dev-shm-usage','--font-render-hinting=none','--hide-scrollbars']});
const out={};
async function plates(page){
  return await page.evaluate(()=>{
    const res=[];
    document.querySelectorAll('#phc-root .benefit').forEach((c,i)=>{
      const t=c.querySelector('.benefit-title'), tx=c.querySelector('.benefit-text'),
            btn=c.querySelector('.benefit-demo');
      const cb=c.getBoundingClientRect(), tb=t.getBoundingClientRect(),
            bb=btn?btn.getBoundingClientRect():null;
      res.push({
        i,
        title:t.textContent.replace(/\s+/g,' ').trim(),
        titleСтрок:Math.round(tb.height/(24*1.2)),
        заголовокПереполнен:t.scrollHeight>t.clientHeight+1,
        текстПереполнен:tx.scrollHeight>tx.clientHeight+1,
        высотаПлашки:Math.round(cb.height),
        низКнопкиВнутриПлашки:bb?Math.round(cb.bottom-bb.bottom):-1,
        текстКнопки:btn?btn.textContent.trim():null,
        кнопкаВидна:bb?bb.width>0&&bb.height>0:false
      });
    });
    return res;
  });
}
const page=await b.newPage();
for (const [имя,шир] of [['desktop',1440],['mobile',390]]){
  await page.setViewport({width:шир,height:1200,deviceScaleFactor:2});
  await page.goto('http://127.0.0.1:8000/calc.html',{waitUntil:'networkidle0',timeout:60000});
  await new Promise(r=>setTimeout(r,700));
  out[имя]=await plates(page);
  const sec=await page.$('#phc-root .benefits');
  if(sec) await sec.screenshot({path:`/home/user/plates-${имя}.png`});
}
/* снимок отчёта: живьём, без скриптов — проверяем, что всё видно */
await page.setViewport({width:1440,height:1200,deviceScaleFactor:1});
await page.goto('http://127.0.0.1:8000/preview.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,700));
out.preview=await page.evaluate(()=>{
  const scr=document.documentElement;
  const скрыто=[...document.querySelectorAll('#phr-root [style*="display:none"],#phr-root .hidden')].length;
  const кольца=[...document.querySelectorAll('#phr-root path[mask]')].map(p=>{
    const d=getComputedStyle(p.closest('path[mask]')).strokeDasharray;return d;});
  const видно= [...document.querySelectorAll('#phr-root [data-block-id]')].filter(e=>{
    const r=e.getBoundingClientRect();return r.height>20;}).length;
  return {страницаВысота:scr.scrollHeight, блоков:document.querySelectorAll('#phr-root [data-block-id]').length,
    блоковВидно:видно, скрытыхБлоков:скрыто, скриптов:document.querySelectorAll('script').length,
    примерDasharray:кольца.slice(0,3), заголовок:document.title};
});
await page.screenshot({path:'/home/user/preview-top.png',clip:{x:0,y:0,width:1440,height:1100}});
console.log(JSON.stringify(out,null,1));
await b.close();
})();
