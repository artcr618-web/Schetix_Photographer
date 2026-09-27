#!/usr/bin/env node
/* Проверяет именно чистый старт calc.html, а не synthetic-сценарий харнесса.

   Требуется `npm --prefix Инструменты ci --ignore-scripts`.
   Запуск:
     node Инструменты/проверить_calc_browser_default.js /путь/к/проекту --assert
     node Инструменты/проверить_calc_browser_default.js /путь/к/проекту --assert --result
     node Инструменты/проверить_calc_browser_default.js /путь/к/проекту --write-snapshot

   Скрипт создаёт новый JSDOM без localStorage, исполняет реальный inline-script
   анкеты и лишь в конце его замыкания добавляет read-only probe. Это нужно,
   потому что calc(), EXC и ФОНД намеренно не глобальные. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const {JSDOM, VirtualConsole} = require('jsdom');

const args = process.argv.slice(2);
const ROOT = path.resolve(args.find(x => !x.startsWith('--')) || path.join(__dirname, '..'));
const SNAPSHOT = path.join(ROOT, 'Инструменты', 'эталоны', 'browser_default_calc.json');
const wantResult = args.includes('--result');
const wantAssert = args.includes('--assert') || (!args.includes('--write-snapshot') && !args.includes('--check-demo') && !wantResult);
const wantWrite = args.includes('--write-snapshot');
const wantDemo = args.includes('--check-demo');
const wantPriceDemo = args.includes('--check-price-demo');

function fail(message) {
  console.error('✗ browser-default:', message);
  process.exitCode = 1;
}
function equal(actual, expected, trail) {
  trail = trail || 'root';
  if (typeof actual === 'number' && typeof expected === 'number') {
    return Math.abs(actual - expected) <= Math.max(1e-9, Math.abs(expected) * 1e-12)
      ? null : `${trail}: ${actual} ≠ ${expected}`;
  }
  if (actual === expected) return null;
  if (!actual || !expected || typeof actual !== 'object' || typeof expected !== 'object')
    return `${trail}: ${JSON.stringify(actual)} ≠ ${JSON.stringify(expected)}`;
  const ak = Object.keys(actual), ek = Object.keys(expected);
  if (ak.length !== ek.length || ak.some(k => !Object.prototype.hasOwnProperty.call(expected, k)))
    return `${trail}: разные ключи`;
  for (const key of ak) {
    const diff = equal(actual[key], expected[key], `${trail}.${key}`);
    if (diff) return diff;
  }
  return null;
}
function extractDemo(source, name) {
  const match = /var\s+DEMO\s*=/.exec(source);
  if (!match) throw Error(`в ${name} нет var DEMO`);
  const brace = source.indexOf('{', match.index + match[0].length);
  let depth = 0, quote = '', escaped = false;
  for (let i = brace; i < source.length; i++) {
    const ch = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) quote = '';
      continue;
    }
    if (ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch === '{') depth++;
    if (ch === '}' && --depth === 0)
      return vm.runInNewContext('(' + source.slice(brace, i + 1) + ')');
  }
  throw Error(`DEMO в ${name} не закрыт`);
}
function assertTaxAutoFlow(window, document, source) {
  const auto = document.getElementById('tax_auto');
  const manual = document.getElementById('taxManual');
  const manualNodes = [...document.querySelectorAll('.tax-manual')];
  const heading = document.getElementById('taxHeading');
  const autoBox = document.getElementById('autoBox');
  const regime = document.getElementById('regime');
  const taxOff = document.getElementById('tax_off');
  const limitToast = document.getElementById('limBar');
  const income = document.getElementById('income_month');
  const change = element => element.dispatchEvent(new window.Event('change', {bubbles: true}));
  const input = element => element.dispatchEvent(new window.Event('input', {bubbles: true}));

  /* Чистый старт — автоматический: ручная зона спрятана, но альтернатива
     «не учитывать налоги» не заблокирована вместе со всей карточкой. */
  if (!auto || !auto.checked) throw Error('автоподбор налогов не включён по умолчанию');
  if (!manual || manual.parentElement?.dataset.blockId !== 'CALC-B008')
    throw Error('вопрос ручного выбора перестал быть прямым вопросом карточки');
  if (!manualNodes.length || manualNodes.some(node => !node.hidden))
    throw Error('при автоподборе видна ручная зона налогов');
  if (heading?.textContent.trim() !== 'Режим налогообложения подбирается автоматически.')
    throw Error('авторежим не переименовал заголовок налогового блока');
  if (autoBox?.querySelector('span')?.textContent.trim() !== 'Настроить вручную')
    throw Error('активная кнопка автоподбора не предлагает ручную настройку');
  if (!autoBox?.querySelector('svg')?.innerHTML.includes('M4 20h4.2'))
    throw Error('активный автоподбор потерял пиктограмму карандаша');
  if (!/#phc-root \.autobtn\{[\s\S]{0,900}background:linear-gradient\(135deg,var\(--c-g-700\),var\(--c-g-500\)\);/.test(source)
      || !/#phc-root \.autobtn:has\(input:checked\)\{\s*\nbackground:var\(--c-g-50\);border-color:var\(--c-g-300\);color:var\(--c-g-800\);box-shadow:none\}/.test(source))
    throw Error('визуальные состояния кнопок авто и ручной настройки не поменяны местами');
  if (!regime.disabled) throw Error('скрытый ручной список режима не заблокирован');
  if (taxOff.disabled) throw Error('автоподбор заблокировал весь налоговый блок');
  if (limitToast.classList.contains('on'))
    throw Error('чистый авторежим показал уведомление о ручной смене НПД');

  /* Ручной путь: при допустимой выручке выбираем НПД, затем повышаем цель.
     Только здесь разрешено сообщать о вынужденном переходе на УСН. */
  auto.checked = false;
  change(auto);
  if (manualNodes.some(node => node.hidden) || regime.disabled)
    throw Error('переход в ручной налоговый режим не открыл поле');
  if (heading?.textContent.trim() !== 'Ваш режим налогообложения')
    throw Error('ручной налоговый режим не вернул исходный заголовок');
  if (autoBox?.querySelector('span')?.textContent.trim() !== 'Выбрать автоматически самый выгодный')
    throw Error('ручная кнопка не предлагает включить автоподбор');
  if (!autoBox?.querySelector('svg')?.innerHTML.includes('M12 2.6'))
    throw Error('ручная настройка потеряла пиктограмму автоматического выбора');
  income.value = '10000';
  input(income);
  const npd = regime.querySelector('option[value="npd"]');
  if (!npd || npd.hidden || npd.disabled) throw Error('НПД не вернулся при выручке в пределах лимита');
  regime.value = 'npd';
  input(regime);
  if (regime.value !== 'npd') throw Error('ручной НПД не установился при допустимой выручке');
  income.value = '110216';
  input(income);
  if (regime.value !== 'usn6') throw Error('ручной НПД не сменился на УСН после превышения лимита');
  if (!limitToast.classList.contains('on') || !limitToast.classList.contains('warn'))
    throw Error('после ручной смены НПД не показано предупреждение');
}

async function browserDefault() {
  const calcPath = path.join(ROOT, 'Веб', 'calc.html');
  let html = fs.readFileSync(calcPath, 'utf8');
  const scriptStart = html.indexOf('<script>');
  const scriptEnd = html.indexOf('</script>', scriptStart);
  /* Основная анкета — один IIFE. Встраиваем probe непосредственно перед
     его финальным закрытием: исполняется реальный lifecycle, но calc не
     приходится публиковать в window для рабочего приложения. */
  const scopeEnd = html.lastIndexOf('\n})();', scriptEnd);
  if (scriptStart < 0 || scriptEnd < 0 || scopeEnd < scriptStart)
    throw Error('не найдено замыкание основного script calc.html');
  const probe = `
window.__phcBrowserDefaultProbe=function(){return {
  result:calc(), exclusions:Object.assign({},EXC),
  fund:{manual:ФОНД.ручной,R:ФОНД.R,investment:ФОНД.инв,recommendation:ФОНД.реком}
};};
`;
  html = html.slice(0, scopeEnd) + probe + html.slice(scopeEnd);

  const runtimeErrors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', error => runtimeErrors.push('JSDOM: ' + error.message));
  const dom = new JSDOM(html, {
    url: 'https://browser-default.schetiks.test/calc.html',
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.scrollTo = () => {};
      window.confirm = () => true;
      window.alert = () => {};
      window.matchMedia = window.matchMedia || (() => ({
        matches: false, addListener() {}, removeListener() {},
        addEventListener() {}, removeEventListener() {}
      }));
      window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.requestAnimationFrame = callback => window.setTimeout(() => callback(Date.now()), 0);
      window.cancelAnimationFrame = id => window.clearTimeout(id);
      window.addEventListener('error', event => runtimeErrors.push('runtime: ' + event.message));
    }
  });
  try {
    await new Promise(resolve => setTimeout(resolve, 50));
    const window = dom.window, document = window.document;
    if (typeof window.__phcBrowserDefaultProbe !== 'function')
      throw Error('основной script calc.html не дошёл до probe');
    const probeResult = window.__phcBrowserDefaultProbe();
    if (runtimeErrors.length) throw Error(runtimeErrors.join('; '));
    const actual = {
      format: 1,
      scenario: 'fresh-calc-html',
      storage: {
        reportAbsent: window.localStorage.getItem('phc_report') === null,
        stateAbsent: window.localStorage.getItem('phc_state') === null
      },
      form: {
        exclusions: probeResult.exclusions,
        controls: {
          regime: document.getElementById('regime').value,
          npdWho: document.getElementById('npd_who').value,
          taxAuto: document.getElementById('tax_auto').checked,
          taxOff: document.getElementById('tax_off').checked,
          fundOn: document.getElementById('fund_on').checked,
          fundPct: document.getElementById('fund_pct').value,
          cushionOn: document.getElementById('cushion_on').checked,
          discOn: document.getElementById('disc_on').checked,
          fmOn: document.getElementById('fm_on').checked
        },
        taxUi: {
          heading: document.getElementById('taxHeading').textContent.trim(),
          manualQuestionIsDirect: document.getElementById('taxManual').parentElement?.dataset.blockId === 'CALC-B008',
          manualHidden: [...document.querySelectorAll('.tax-manual')].every(node => node.hidden),
          manualSelectDisabled: document.getElementById('regime').disabled,
          autoButtonLabel: document.querySelector('#autoBox span').textContent.trim(),
          taxOffEnabled: !document.getElementById('tax_off').disabled,
          limitToastVisible: document.getElementById('limBar').classList.contains('on')
        },
        fund: probeResult.fund
      },
      result: probeResult.result
    };
    assertTaxAutoFlow(window, document, fs.readFileSync(calcPath, 'utf8'));
    return actual;
  } finally {
    dom.window.close();
  }
}

(async () => {
  const actual = await browserDefault();
  if (!actual.storage.reportAbsent || !actual.storage.stateAbsent)
    throw Error('новый browser-default тест получил не пустое localStorage');

  if (wantWrite) {
    fs.mkdirSync(path.dirname(SNAPSHOT), {recursive: true});
    fs.writeFileSync(SNAPSHOT, JSON.stringify(actual, null, 2) + '\n');
    console.error('✓ browser-default snapshot записан: ' + path.relative(ROOT, SNAPSHOT));
  }
  if (wantAssert) {
    if (!fs.existsSync(SNAPSHOT)) throw Error('нет golden snapshot: ' + path.relative(ROOT, SNAPSHOT));
    const expected = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));
    const diff = equal(actual, expected);
    if (diff) throw Error('fresh calc.html разошёлся с golden snapshot: ' + diff);
    console.error('✓ browser-default fresh calc.html совпадает с golden snapshot');
  }
  if (wantDemo) {
    const demo = extractDemo(fs.readFileSync(path.join(ROOT, 'Веб', 'report.html'), 'utf8'), 'report.html');
    const diff = equal(demo, actual.result, 'DEMO');
    if (diff) throw Error('технический DEMO разошёлся с browser default: ' + diff);
    console.error('✓ report DEMO совпадает с browser-default result');
  }
  if (wantPriceDemo) {
    const priceDemo = extractDemo(fs.readFileSync(path.join(ROOT, 'Веб', 'price.html'), 'utf8'), 'price.html');
    const keys = ['K', 'NT', 'R', 'S', 'cl', 'discP', 'pool', 'rateWorkFull', 'sh'];
    const expected = Object.fromEntries(keys.map(key => [key, actual.result[key]]));
    const diff = equal(priceDemo, expected, 'price DEMO');
    if (diff) throw Error('DEMO прайса разошёлся с browser default: ' + diff);
    console.error('✓ price DEMO использует нужные поля browser-default result');
  }
  if (wantResult) process.stdout.write(JSON.stringify(actual.result));
})().catch(error => fail(error && error.message ? error.message : String(error)));
