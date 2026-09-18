const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
await page.setViewport({width:1440,height:1200,deviceScaleFactor:2});
await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,700));
await (await page.$('#phc-root .benefits-grid')).screenshot({path:'/home/user/final-plates.png'});
for (const id of ['CALC-B012','CALC-B040']){
  await (await page.$(`#phc-root .card[data-block-id="${id}"]`)).screenshot({path:`/home/user/final-${id}.png`});
}
await b.close();})();
