const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();await page.setViewport({width:1440,height:1200});
await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,700));
console.log(JSON.stringify(await page.evaluate(`(()=>{
 const out={режим:document.compatMode,блоки:[]};
 document.querySelectorAll('#phc-root [data-block-id]').forEach(e=>{
  const r=e.getBoundingClientRect();
  out.блоки.push({id:e.getAttribute('data-block-id'),имя:e.getAttribute('data-block-name'),
   top:Math.round(r.top+scrollY),h:Math.round(r.height)});});
 const img=[...document.images].length, imgПровис=[...document.images].filter(i=>i.getBoundingClientRect().height>0).length;
 out.картинок=img; out.видимыхКартинками=imgПровис;
 out.таблиц=document.querySelectorAll('#phc-root table').length;
 return out;})()`),null,0));
await b.close();})();
