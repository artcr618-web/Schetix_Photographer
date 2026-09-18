const puppeteer=require('/home/user/measure/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--hide-scrollbars']});
const page=await b.newPage();
await page.setViewport({width:1440,height:900,deviceScaleFactor:2});
await page.goto('http://127.0.0.1:8001/preview.html',{waitUntil:'networkidle0',timeout:60000});
await new Promise(r=>setTimeout(r,400));
const до=await page.evaluate(()=>{
 const п=document.querySelector('#phr-root .tbar');
 const к=п.querySelector('.pv-cta'), br=п.querySelector('.brand');
 const kb=к.getBoundingClientRect(), bb=br.getBoundingClientRect(), pb=п.getBoundingClientRect();
 return {кнопок_в_панели:п.querySelectorAll('a,button').length,
  кнопка:к.textContent.trim(), href:к.getAttribute('href'),
  размер:Math.round(kb.width)+'x'+Math.round(kb.height),
  цветфона:getComputedStyle(к).backgroundImage.slice(0,44),
  логотипСправа:Math.round(bb.left-pb.left)>Math.round(kb.left-pb.left),
  позиция:getComputedStyle(п).position, высотаПанели:Math.round(pb.height),
  значков_осталось:п.querySelectorAll('.fbi,.fbl').length,
  дубльМеню:!!document.querySelector('#fbar'),
  скриптов:document.scripts.length,
  высотаСтраницы:document.documentElement.scrollHeight};});
await page.evaluate(()=>scrollTo(0,1200));
await new Promise(r=>setTimeout(r,300));
const после=await page.evaluate(()=>{
 const п=document.querySelector('#phr-root .tbar');const r=п.getBoundingClientRect();
 const к=п.querySelector('.pv-cta').getBoundingClientRect();
 const под=document.elementFromPoint(720,Math.round(r.bottom)+6);
 return {панельtop:Math.round(r.top),кнопкавидна:к.top>=0&&к.bottom<=innerHeight,
  под_панелью:под?под.closest('#phr-root .tbar')?'панель':'контент':'нет',тень:getComputedStyle(п).borderBottomWidth};});
await page.evaluate(()=>scrollTo(0,0));await new Promise(r=>setTimeout(r,250));
await page.screenshot({path:'/home/user/pv-new-head.png',clip:{x:0,y:0,width:1440,height:260}});
/* переход по кнопке */
await page.click('#phr-root .pv-cta');await new Promise(r=>setTimeout(r,900));
const url=page.url();
console.log(JSON.stringify({до,после,клик_ведёт:url},null,1));
await b.close();})();
