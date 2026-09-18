const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
const URL='http://127.0.0.1:8001/calc.html';

async function мерка(page){
  return await page.evaluate(()=>{
    const р=[];
    document.querySelectorAll('#phc-root .benefit').forEach((c,i)=>{
      const t=c.querySelector('.benefit-title'), tx=c.querySelector('.benefit-text'),
            btn=c.querySelector('.benefit-demo');
      const r=document.createRange(); r.selectNodeContents(t);
      const строк=r.getClientRects().length;
      const cs=getComputedStyle(t), cb=c.getBoundingClientRect(), tb=t.getBoundingClientRect(),
            bb=btn.getBoundingClientRect();
      р.push({
        плашка:i,
        заголовок:t.textContent.replace(/\s+/g,' ').trim(),
        строкЗаголовка:строк,
        lineСз:cs.lineHeight, кегль:cs.fontSize,
        boxВысота:Math.round(tb.height), boxДоступно:Math.round(t.clientHeight),
       переполнение:t.scrollHeight>t.clientHeight+1,
        переполнениеТекста:Math.round(tb.height - t.clientHeight)>1,
        строкаПодЧертойY:Math.round(tb.bottom - cb.top),
        плашкаВысота:Math.round(cb.height),
        отступКнопкиСнизу:Math.round(cb.bottom-bb.bottom),
        текстПодЧертой:tx.textContent.replace(/\s+/g,' ').trim(),
        текстСтрок:(()=>{const q=document.createRange();q.selectNodeContents(tx);return q.getClientRects().length})(),
        шрифтЗаголовка:cs.fontFamily.split(',')[0]
      });
    });
    const tail=document.querySelector('#phc-root .benefits-tail');
    const grid=document.querySelector('#phc-root .benefits-grid');
    return {плашки:р,
      рядПлашекВысота:Math.round(grid.getBoundingClientRect().height),
      хвостОтступСверху:Math.round(parseFloat(getComputedStyle(tail).marginTop)),
      ширинаКолонки:Math.round(document.querySelector('#phc-root .benefit').getBoundingClientRect().width),
      переполненоКарточек:[...document.querySelectorAll('#phc-root .benefit')].filter(e=>e.scrollHeight>e.clientHeight+1).length};
  });
}
(async()=>{
  const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',
    args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
  const page=await b.newPage(); const out={};
  for (const [имя,w,h] of [['десктоп',1440,1200],['ноут',1180,900],['мобильный',390,900]]){
    await page.setViewport({width:w,height:h,deviceScaleFactor:имя==='десктоп'?2:1});
    await page.goto(URL,{waitUntil:'networkidle0',timeout:60000});
    await new Promise(r=>setTimeout(r,600));
    out[имя]=await мерка(page);
  }
  await page.setViewport({width:1440,height:1200,deviceScaleFactor:2});
  await page.goto(URL,{waitUntil:'networkidle0',timeout:60000});
  await new Promise(r=>setTimeout(r,600));
  const sec=await page.$('#phc-root .benefits');
  await sec.screenshot({path:'/home/user/places-final.png'});
  console.log(JSON.stringify(out,null,1));
  await b.close();
})();
