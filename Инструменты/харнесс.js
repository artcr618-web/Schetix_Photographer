/* Выполняет НАСТОЯЩИЕ calc() из web/calc.html и parts() из web/report.html
   на подставленных значениях полей — без браузера.
   Запуск: node харнесс.js [корень] [json-переопределений]           */
const fs = require('fs');
const КОРЕНЬ = process.argv[2] || '/home/user/schetix';
const ПЕРЕОПР = process.argv[3] ? JSON.parse(process.argv[3]) : {};

const calcHtml = fs.readFileSync(КОРЕНЬ + '/Веб/calc.html', 'utf8');
const repHtml  = fs.readFileSync(КОРЕНЬ + '/Веб/report.html', 'utf8');
const js = s => s.match(/<script[^>]*>([\s\S]*?)<\/script>/g).map(x => x.replace(/<\/?script[^>]*>/g, '')).join('\n');
const CJS = js(calcHtml), RJS = js(repHtml);

/* --- вырезаем куски настоящего кода --- */
function срез(текст, начало, конецМаркер) {
  const i = текст.indexOf(начало);
  if (i < 0) throw new Error('не найдено: ' + начало);
  const j = текст.indexOf(конецМаркер, i);
  return текст.slice(i, j + конецМаркер.length);
}
function функция(текст, имя) {                 // вырезает function имя(){...} по балансу скобок
  const i = текст.indexOf('function ' + имя + '(');
  if (i < 0) throw new Error('нет функции ' + имя);
  let g = 0, начал = false;
  for (let p = i; p < текст.length; p++) {
    const c = текст[p];
    if (c === '{') { g++; начал = true; }
    else if (c === '}') { g--; if (начал && g === 0) return текст.slice(i, p + 1); }
  }
  throw new Error('не закрыта ' + имя);
}
const КОНСТ1 = срез(CJS, 'var FIX=', 'WM=11;');
const КОНСТ2 = срез(CJS, 'var WD=', 'DW=5;');
const КОНСТ3 = срез(CJS, 'var ND=WD-VAC-SICK', ';');
const КАТ    = срез(CJS, 'var CAT={', '\nvar EXC={').replace('\nvar EXC={', '');
const ФКАТИСКЛ = функция(CJS, 'каталогИсключён');
const ФКАЛК  = функция(CJS, 'calc')
  + (CJS.includes('function посчитать(') ? '\nvar _кэш=null;\nfunction сброситьКэш(){_кэш=null}\n' + функция(CJS, 'посчитать') : '');
const ФПАРТС = функция(RJS, 'parts');

/* --- значения полей формы: берём фактические value= из разметки --- */
const ПОЛЯ_ВНЕШ = {};
const разметка = calcHtml.replace(/<script[\s\S]*?<\/script>/g, '');
for (const m of разметка.matchAll(/<input\b[^>]*>/g)) {
  const t = m[0];
  const id = (t.match(/id="([^"]+)"/) || [])[1];
  if (!id) continue;
  const тип = (t.match(/type="?([\w-]+)/) || [])[1] || 'text';
  if (тип === 'checkbox' || тип === 'radio') ПОЛЯ_ВНЕШ[id] = /\bchecked\b/.test(t);
  else ПОЛЯ_ВНЕШ[id] = (t.match(/value="([^"]*)"/) || ['', ''])[1];
}
for (const m of разметка.matchAll(/<select\b[^>]*id="([^"]+)"[\s\S]*?<\/select>/g)) {
  const блок = m[0], id = m[1];
  const выбр = блок.match(/<option value="([^"]*)"[^>]*selected/) || блок.match(/<option value="([^"]*)"/);
  ПОЛЯ_ВНЕШ[id] = выбр ? выбр[1] : '';
}
const РАДИО_ВНЕШ = {};
for (const m of разметка.matchAll(/<input[^>]*type="radio"[^>]*>/g)) {
  const t = m[0];
  const n = (t.match(/name="([^"]+)"/) || [])[1], v = (t.match(/value="([^"]*)"/) || [])[1];
  if (n && (!(n in РАДИО_ВНЕШ) || /\bchecked\b/.test(t))) РАДИО_ВНЕШ[n] = v;
}
Object.assign(ПОЛЯ_ВНЕШ, ПЕРЕОПР.поля || {});
Object.assign(РАДИО_ВНЕШ, ПЕРЕОПР.радио || {});
const EXC_ВНЕШ = Object.assign({}, ПЕРЕОПР.EXC_ВНЕШ || {});

/* --- шим окружения --- */
const шим = `
${КОНСТ1}
${КОНСТ2}
${КОНСТ3}
${КАТ}
var CAT_OVERRIDE=${JSON.stringify(ПЕРЕОПР.CAT || {})};
Object.keys(CAT_OVERRIDE).forEach(function(k){CAT[k]=CAT_OVERRIDE[k]});
var ПОЛЯ=${JSON.stringify(ПОЛЯ_ВНЕШ)}, РАДИО=${JSON.stringify(РАДИО_ВНЕШ)}, EXC=${JSON.stringify(EXC_ВНЕШ)};
var BANK_ACQ_ON = ${ПЕРЕОПР.BANK_ACQ_ON === false ? 'false' : 'true'};
var ДОПКОМИССИИ = ${JSON.stringify(ПЕРЕОПР.допКомиссии || 0)};
var УДАЛЕНЫ = ${JSON.stringify(ПЕРЕОПР.удалены || [])};
function число(v){ v=String(v==null?'':v).replace(/\\s|\\u00a0/g,'').replace(',', '.'); var n=parseFloat(v); return isFinite(n)?n:0 }
function V(id){ return число(ПОЛЯ[id]) }
function CHK(id){ return !!ПОЛЯ[id] }
function rad(n){ return РАДИО[n] || '' }
function списокДопКомиссий(){
  if(Array.isArray(ДОПКОМИССИИ))return ДОПКОМИССИИ.map(function(x){
    return Array.isArray(x)?{name:String(x[0]||''),rate:число(x[1])}:{name:String(x.name||''),rate:число(x.rate)};
  });
  return число(ДОПКОМИССИИ)?[{name:'Дополнительная комиссия',rate:число(ДОПКОМИССИИ)}]:[];
}
function суммаДопКомиссий(){ return списокДопКомиссий().reduce(function(s,x){return s+x.rate},0) }
function $(id){
  if(id==='regime') return {value: ПОЛЯ.regime};
  if(id==='npd_who') return {value: ПОЛЯ.npd_who};
  if(id==='fm_on')   return {checked: !!ПОЛЯ.fm_on};
  if(id==='t_Form006') return {querySelectorAll:function(){ 
      return CAT.Form006.rows.map(function(r){ return {querySelector:function(s){ 
        return {value: s==='.c2'? r[1] : r[2]} }} }) }};
  if(id in ПОЛЯ) return {value:ПОЛЯ[id],checked:!!ПОЛЯ[id],closest:function(sel){
      if(sel==='.removable-field-row'&&УДАЛЕНЫ.indexOf(id)>=0)
        return {classList:{contains:function(c){return c==='field-row-removed'}}};
      return null;
    }};
  return null;
}
${ФКАТИСКЛ}
/* sumF поверх CAT использует тот же слой исключения, что оригинал. */
function sumF(f){
  if(каталогИсключён(f)) return 0;
  var c=CAT[f]; if(!c) return 0; var s=0;
  c.rows.forEach(function(r){ var цена=r[1], x=r[2];
    if(c.k==='months') return;
    s += (c.k==='life') ? (x>0?цена/x:0) : цена*x; });
  return s;
}
function regimeName(rg){ return String(rg) }
var PROF='\u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0430';
${ФКАЛК}
${ФПАРТС}
var d = calc();
d.__parts = parts({NT:d.NT, idle:d.idle, Ny:d.Ny, sh:d.sh, post:d.post, clT:d.clT, promo:d.promo,
  accT:d.accT, fmT:d.fmT, equip:d.equip, promoM:d.promoM, depShoot:d.depShoot, depOffice:d.depOffice,
  depSoft:d.depSoft, depEdu:d.depEdu, depSite:d.depSite, depWs:d.depWs, varAds:d.varAds,
  varSoft:d.varSoft, varBank:d.varBank, varRent:d.varRent, varAcc:d.varAcc,
  taxAll:d.taxAll, aq:d.aq, fundY:d.fundY, discY:d.discY});
console.log(JSON.stringify(d));
`;
try { eval(шим); } catch (e) { console.error('ОШИБКА ХАРНЕССА: ' + e.message); process.exit(2); }
