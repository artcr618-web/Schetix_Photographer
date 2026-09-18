const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
for(const [имя,w] of [['1440',1440],['1024',1024]]){
 await page.setViewport({width:+w,height:1000,deviceScaleFactor:2});
 await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
 await new Promise(r=>setTimeout(r,500));
 await (await page.$('#phc-root .benefits-grid')).screenshot({path:`/home/user/pl-${имя}-new.png`});
}
await b.close();})();
