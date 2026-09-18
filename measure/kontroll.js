const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
await page.setViewport({width:1440,height:1200,deviceScaleFactor:2});
/* сервер БЕЗ charset в заголовке — именно так страница вела себя до правки */
await page.goto('http://127.0.0.1:8002/calc.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,600));
console.log('кодировка заголовка: без charset; заголовок вкладки =',await page.title());
const плашки=await page.evaluate(()=>[...document.querySelectorAll('#phc-root .benefit')].map(c=>({
  заголовок:c.querySelector('.benefit-title').textContent.trim(),
  подпись:c.querySelector('.benefit-text').textContent.replace(/\s+/g,' ').trim(),
  ссылка:c.querySelector('.benefit-demo').textContent.trim(),
  высота:Math.round(c.getBoundingClientRect().height)})));
console.log(JSON.stringify(плашки,null,1));
await (await page.$('#phc-root .benefits-grid')).screenshot({path:'/home/user/v-plates.png'});
await (await page.$('#phc-root .card[data-block-id="CALC-B015"]')).screenshot({path:'/home/user/v-b10.png'});
await page.setViewport({width:390,height:900,deviceScaleFactor:2});
await page.reload({waitUntil:'networkidle0'});
await new Promise(r=>setTimeout(r,500));
await (await page.$('#phc-root .benefits')).screenshot({path:'/home/user/v-plates-mobile.png'});
await b.close();})();
