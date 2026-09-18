const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();const out={};
for(const [имя,w,h,dpr] of [['десктоп',1440,1200,2],['мобильный',390,900,1]]){
 await page.setViewport({width:w,height:h,deviceScaleFactor:dpr});
 await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
 await new Promise(r=>setTimeout(r,700));
 out[имя]=await page.evaluate(()=>{
  const метки=[];
  document.querySelectorAll('#phc-root .card .time-category-direct,#phc-root .card .time-category-system').forEach(sp=>{
   const p=sp.closest('p');
   const r=document.createRange();r.selectNodeContents(p);
   const строки=[...r.getClientRects()].filter(x=>x.height>0);
   const м=sp.getBoundingClientRect();
   /* строка, непосредственно предшествующая маркировке */
   const до=строки.filter(x=>x.top<м.top-1);
   const пред=до[до.length-1];
   метки.push({блок:p.closest('.card').getAttribute('data-block-id'),
    шаг:Math.round((м.top-пред.top)*10)/10, межстрочный:getComputedStyle(p).lineHeight,
    gap:Math.round((м.top-пред.bottom)*10)/10});
  });
  const плашки=[...document.querySelectorAll('#phc-root .benefit')].map(c=>{
   const cb=c.getBoundingClientRect(),ab=c.querySelector('.benefit-demo').getBoundingClientRect();
   const t=c.querySelector('.benefit-text');
   return {высота:Math.round(cb.height),низСсылки:Math.round(cb.bottom-ab.bottom),
    зазорТекстДоСсылки:Math.round(ab.top-t.getBoundingClientRect().bottom)};});
  return {метки,плашки,ряд:Math.round(document.querySelector('#phc-root .benefits-grid').getBoundingClientRect().height)};
 });
}
console.log(JSON.stringify(out,null,1));await b.close();})();