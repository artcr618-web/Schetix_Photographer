/* Рендерит рабочий report или кандидата в jsdom по DEMO. */
const fs=require('fs'),path=require('path');
const {JSDOM,VirtualConsole}=require('/tmp/jsdom-env/node_modules/jsdom');
const file=process.argv[2]; if(!file)throw Error('Укажите HTML');
const dataFile=process.argv[3]||'';
const injected=dataFile?JSON.parse(fs.readFileSync(dataFile,'utf8')):null;
if(injected)injected._ts=Date.now();
const html=fs.readFileSync(file,'utf8'), errors=[];
const vc=new VirtualConsole(); vc.on('jsdomError',e=>errors.push(e.message)); vc.on('error',e=>errors.push(String(e)));
const dom=new JSDOM(html,{url:'https://schetix.test/report.html'+(injected?'':'?demo=1'),runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
 if(injected)w.localStorage.setItem('phc_report',JSON.stringify(injected));
 w.scrollTo=()=>{}; w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
 w.IntersectionObserver=class{observe(){} unobserve(){} disconnect(){}};
 if(!w.URL.createObjectURL)w.URL.createObjectURL=()=>'';
 if(!w.URL.revokeObjectURL)w.URL.revokeObjectURL=()=>{};
}});
setTimeout(()=>{
 const d=dom.window.document;
 const text=id=>{const x=d.getElementById(id);return x?x.textContent.replace(/\s+/g,' ').trim():''};
 const out={errors,blocks:d.querySelectorAll('[data-block-id]').length,page:d.querySelector('#phr-root')?.dataset.pageId||'',
 hero:text('heroRate')||text('heroVal'),scenarios:text('dns'),loyalty:text('fnd'),details:text('fullTab'),
 zeroText:(text('dns').match(/\d+ съём\S* в месяц[^.]{0,120}/)||[])[0]||'',
 bodyText:d.body.textContent.replace(/\s+/g,' ').trim().slice(0,500)};
 console.log(JSON.stringify(out));
},700);
