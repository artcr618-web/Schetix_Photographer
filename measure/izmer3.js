const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
const URL='http://127.0.0.1:8001/calc.html';
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',
  args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();const out={};
for(const [имя,w,h,dpr] of [['десктоп',1440,1200,2],['мобильный',390,900,1]]){
  await page.setViewport({width:w,height:h,deviceScaleFactor:dpr});
  await page.goto(URL,{waitUntil:'networkidle0',timeout:60000});
  await new Promise(r=>setTimeout(r,700));
  out[имя]=await page.evaluate(()=>{
    /* 1. маркировка отдельной строкой: интервал между последней строкой
          подзаголовка и строкой маркировки = обычный межстрочный */
    const метки=[];
    document.querySelectorAll('#phc-root .card .time-category-direct,#phc-root .card .time-category-system')
      .forEach(sp=>{
        const p=sp.closest('p');
        const r=document.createRange();r.setStart(p.firstChild,0);r.setEnd(p.firstChild,p.firstChild.textContent.length);
        const строки=[...r.getClientRects()];
        const последняя=строки[строки.length-1];
        const м=sp.getBoundingClientRect();
        const cs=getComputedStyle(sp), pcs=getComputedStyle(p);
        метки.push({блок:p.closest('.card').dataset.blockId?p.closest('.card').dataset.blockId.slice(-4):'?',
          текст:sp.textContent.trim(),
          цвет:cs.color, кегль:cs.fontSize, жирность:cs.fontWeight,
          межстрочный:cs.lineHeight,
          строкПодзаголовка:строки.length,
          шагМеждуСтроками:Math.round((м.top-последняя.top)*10)/10,
          extraОтступ:Math.round((м.top-последняя.bottom)*10)/10,
          padding:cs.padding, margin:cs.margin});
      });
    /* 2. плашки: ссылка без рамки и подложки */
    const плашки=[];
    document.querySelectorAll('#phc-root .benefit').forEach((c,i)=>{
      const a=c.querySelector('.benefit-demo'), cs=getComputedStyle(a);
      const cb=c.getBoundingClientRect(), ab=a.getBoundingClientRect();
      плашки.push({i,высотаПлашки:Math.round(cb.height),текст:a.textContent.trim(),
        рамка:cs.borderTopWidth+' '+cs.borderStyle, подложка:cs.backgroundColor,
        радиус:cs.borderTopLeftRadius, кегль:cs.fontSize, стрелка:!!a.querySelector('svg'),
        ширинаСсылки:Math.round(ab.width), высота:Math.round(ab.height),
        отступСнизу:Math.round(cb.bottom-ab.bottom), слеваОтПлашки:Math.round(ab.left-cb.left)});
    });
    const grid=document.querySelector('#phc-root .benefits-grid');
    return {метки,плашки,ряд:Math.round(grid.getBoundingClientRect().height)};
  });
  const el=await page.$('#phc-root .benefits');await el.screenshot({path:`/home/user/shot-plates-${имя}.png`});
  const card=await page.$('#phc-root .card[data-block-id="CALC-B012"]');
  await card.screenshot({path:`/home/user/shot-b06-${имя}.png`});
}
console.log(JSON.stringify(out,null,1));
await b.close();
})();
