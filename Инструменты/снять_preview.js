#!/usr/bin/env node
/* Снимает статическую страницу Веб/preview.html — снимок демо-отчёта.
   Как и положено снимку: только разметка, стили и готовые числа.
   Формул, расчётного кода и данных анкеты в файле не остаётся —
   все <script> вырезаются, а секторы колец переводятся в конечное
   состояние (иначе без JS они остались бы скрытыми под маской).

   Запуск:  node Инструменты/снять_preview.js [корень_репозитория]
   Перед съёмкой демо-набор в report.html должен быть актуальным:
   node Инструменты/демо.py   (проверка следит, чтобы он совпадал с
   расчётом по значениям по умолчанию).
   Снимок снимается с report.html в режиме ?demo=1, то есть по тем же
   значениям анкеты по умолчанию, без ввода данных посетителем. */
const fs = require('fs'), path = require('path');
let JSDOM, VirtualConsole;
try { ({ JSDOM, VirtualConsole } = require('jsdom')); }
catch (e) {
  console.error('Не установлен jsdom. Выполните npm ci в папке Инструменты.');
  process.exit(3);
}
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const SRC = path.join(ROOT, 'Веб', 'report.html');
const OUT = path.join(ROOT, 'Веб', 'preview.html');
const html = fs.readFileSync(SRC, 'utf8');
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => { if (e.message !== 'Could not parse CSS stylesheet') errors.push(e.message); });
vc.on('error', e => errors.push(String(e)));

/* IntersectionObserver в jsdom отсутствует — и это нужно: отчёт сам
   показывает всё сразу («старый браузер: показываем без анимации»),
   поэтому в снимок попадает конечное, а не стартовое состояние. */
const dom = new JSDOM(html, {
  url: 'https://schetix.test/report.html?demo=1',
  runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc,
  beforeParse(w) {
    w.scrollTo = () => {};
    w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
    if (!w.URL.createObjectURL) w.URL.createObjectURL = () => '';
    if (!w.URL.revokeObjectURL) w.URL.revokeObjectURL = () => {};
  }
});

const wait = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  await wait(1500);
  const d = dom.window.document, root = d.querySelector('#phr-root');
  if (!root) throw Error('#phr-root не отрисован');
  const цифры = root.textContent.replace(/\s+/g, ' ').trim().length;
  if (цифры < 20000) throw Error('отчёт не собрался: в разметке всего ' + цифры + ' знаков');

  /* Секторы колец: маска спрятана штрихом «0 длина», а раскрытие делает
     <animate begin="indefinite"> из скрипта. В статичном снимке скрипта
     нет, поэтому переносим конечное значение анимации прямо в атрибут. */
  let секторы = 0;
  root.querySelectorAll('animate.segan').forEach(a => {
    const path = a.parentNode, to = a.getAttribute('to');
    if (path && to) { path.setAttribute('stroke-dasharray', to); секторы++; }
    a.remove();
  });
  root.querySelectorAll('.anim-ring,.anim-bar,.anim-wk').forEach(e => e.classList.add('go'));

  /* Меню превью — своё (18.09, слово владельца). В отчёте оно остаётся
     как есть, а здесь из него убраны четыре значка: «сохранить»,
     «поделиться» и «поблагодарить» без скриптов всё равно не работают,
     а «редактировать» дублирует нужную кнопку. Слева остаётся одна
     большая кнопка «Заполнить анкету» — обычная ссылка на calc.html,
     без единой строки кода. Логотип на месте, справа.
     Панель сделана липкой (position:sticky) — это чистый CSS, работает
     и в статичном снимке: при прокрутке меню всплывает над страницей. */
  const панель=root.querySelector('.tbar');
  if(панель){
    панель.querySelector('nav.tbn')?.remove();
    const кнопка=d.createElement('a');
    кнопка.className='pv-cta'; кнопка.href='calc.html';
    кнопка.textContent='Заполнить анкету';
    панель.prepend(кнопка);
  }
  root.querySelector('#fbar')?.remove();           /* дубль меню без JS мёртв */
  const стиль=d.createElement('style');
  стиль.textContent=`
/* Превью: своё меню — липкая панель с кнопкой анкеты и логотипом. */
#phr-root .tbar{position:sticky;top:0;z-index:70;padding:10px 0;margin:-12px 0 26px;
border-bottom:1px solid var(--c-ln)}
#phr-root .pv-cta{display:inline-flex;align-items:center;justify-content:center;height:46px;
padding:0 24px;border-radius:14px;background:linear-gradient(135deg,var(--c-g-800),var(--c-g-500));
color:var(--c-white);font-size:15px;font-weight:600;letter-spacing:-.01em;text-decoration:none;
box-shadow:0 4px 16px rgba(33,160,56,.24);transition:.16s}
#phr-root .pv-cta:hover{background:linear-gradient(135deg,var(--c-g-900),var(--c-g-600));
box-shadow:0 6px 20px rgba(33,160,56,.3)}
#phr-root .pv-cta:active{transform:translateY(1px);box-shadow:0 3px 10px rgba(33,160,56,.24)}
#phr-root .pv-cta:focus-visible{outline:2px solid var(--c-g-500);outline-offset:3px}
@media(max-width:700px){#phr-root .tbar{gap:12px;padding:8px 0}
#phr-root .pv-cta{height:42px;padding:0 16px;font-size:14px}}
`;
  d.head.appendChild(стиль);

  /* Никакого кода: ни расчётов, ни обработчиков. */
  const удалено = root.querySelectorAll('script').length;
  root.querySelectorAll('script').forEach(s => s.remove());
  d.querySelectorAll('head script, body > script').forEach(s => s.remove());

  d.title = 'Счётикс — пример отчёта';
  const meta = d.createElement('meta');
  meta.name = 'robots'; meta.content = 'noindex';
  d.head.appendChild(meta);

  fs.writeFileSync(OUT, '<!DOCTYPE html>\n' + d.documentElement.outerHTML + '\n');
  const размер = fs.statSync(OUT).size;
  console.log(JSON.stringify({
    ок: !errors.length, ошибокJS: errors.length,
    секторовКолец: секторы, скриптовУдалено: удалено,
    знаковТекста: цифры, размерКБ: Math.round(размер / 1024),
    файл: path.relative(ROOT, OUT), ошибки: errors.slice(0, 3)
  }));
  if (errors.length) process.exit(1);
})();
