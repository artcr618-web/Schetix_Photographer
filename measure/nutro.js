const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();await page.setViewport({width:1440,height:1200});
await page.goto('http://127.0.0.1:8001/calc.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,600));
console.log(JSON.stringify(await page.evaluate(`(()=>{
 const кар=document.querySelector('#phc-root .card[data-block-id="CALC-B015"]');
 const обход=(эл,глубина,аккум)=>{ for(const c of эл.children){
   const r=c.getBoundingClientRect();
   аккум.push({путь:глубина+'/'+c.tagName.toLowerCase()+(c.className&&typeof c.className==='string'?'.'+c.className.trim().split(/\\s+/).join('.'):''),
     h:Math.round(r.height*100)/100,w:Math.round(r.width*100)/100,
     lh:getComputedStyle(c).lineHeight,va:getComputedStyle(c).verticalAlign,d:getComputedStyle(c).display,
     mt:getComputedStyle(c).marginTop,mb:getComputedStyle(c).marginBottom});
   if(глубина<3) обход(c,глубина+1,аккум);} return аккум;};
 return {режим:document.compatMode,элементы:обход(кар,0,[])}})()`)));
await b.close();})();
