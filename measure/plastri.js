const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
for(const [имя,w,h,dpr] of [['десктоп',1440,1200,2],['мобильный',390,900,2]]){
 await page.setViewport({width:w,height:h,deviceScaleFactor:dpr});
 await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
 await new Promise(r=>setTimeout(r,600));
 const m=await page.evaluate(()=>{
  const плашки=[...document.querySelectorAll('#phc-root .benefit')].map(c=>{
   const cb=c.getBoundingClientRect(),t=c.querySelector('.benefit-title'),a=c.querySelector('.benefit-demo');
   const tb=t.getBoundingClientRect(),ab=a.getBoundingClientRect(),cs=getComputedStyle(a);
   return {заголовок:t.textContent.replace(/\s+/g,' ').trim(),
    плашка:Math.round(cb.height),строкЗаголовка:(()=>{const r=document.createRange();r.selectNodeContents(t);return [...r.getClientRects()].filter(x=>x.height>0).length})(),
    ссылкаСверхуОтЧёрты:Math.round(ab.top-tb.bottom),ссылкаВнизу:Math.round(cb.bottom-ab.bottom),
    кегль:cs.fontSize,вес:cs.fontWeight,межстрочный:cs.lineHeight,цвет:cs.color,
    текст:a.textContent.trim(),стрелка:!!a.querySelector('svg'),
    ширинаСсылки:Math.round(ab.width),высота:Math.round(ab.height)};});
  return {плашки,ряд:Math.round(document.querySelector('#phc-root .benefits-grid').getBoundingClientRect().height),
   высотаСтраницы:document.documentElement.scrollHeight,режим:document.compatMode};});
 console.log('###',имя);console.log(JSON.stringify(m,null,1));
 await (await page.$('#phc-root .benefits-grid')).screenshot({path:`/home/user/pl-${имя}.png`});
}
await b.close();})();
