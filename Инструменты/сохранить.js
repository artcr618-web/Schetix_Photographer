/* ═══════════ ОКНО «СОХРАНИТЬ ДОКУМЕНТ» · общий файл (решение владельца 04.09) ═══════════

   Одно окно на все документы: отчёт (report.html) и прайс (price.html).
   Дизайн повторяет канон окна «Поделиться» (.shm из report.html): ширина 500,
   радиус 20, крестик справа сверху, закрытие по Esc и по фону, ряд плиток
   44×44 с подписью при наведении. Меняется здесь — меняется на всех страницах.

   ПОДКЛЮЧЕНИЕ — одной строкой в конце страницы, после её собственных скриптов:
       <script src="Окна/сохранить.js"></script>

   НАПОЛНЕНИЕ — страница описывает свой документ (до первого клика):
       window.СЧХДокумент = {
         заголовок:   'Сохранить отчёт',                 // заголовок окна
         описание:    '…',                               // строка под заголовком
         имяФайла:    function(){ return 'Имя файла' },  // без расширения, .html добавит окно
         напечатать:  function(){ … },                   // печать / сохранение в PDF
         собратьФайл: function(){ return Promise<html> },// самодостаточный HTML документа
         письмо:      { тема: '…', текст: '…' }          // черновик письма для «Написать письмо»
       };
     Любое поле может быть функцией — тогда берётся её результат.
     Нет собратьФайл — плитки «Скачать» и «Отправить» не показываются;
     нет напечатать — не показывается плитка печати.

   ОТКРЫТЬ ОКНО: СЧХСохранить()   (страницы держат запасной путь —
     печать напрямую, — если этот файл не подключился).

   ДЕЙСТВИЯ:
     «Скачать файл»                   — файл документа уходит в загрузки;
     «Напечатать или сохранить в PDF» — системный диалог печати страницы;
     «Отправить»                      — системное окно «Поделиться» с файлом
        (телефоны, Windows): мессенджер, соцсеть, почта. Где такого окна нет
        (настольные браузеры без Web Share), файл уходит в загрузки, а плашка
        предлагает «Написать письмо» — открывается почтовая программа с темой
        и текстом, файл остаётся приложить вручную.

   ПОМОЩНИК: СЧХСохранить.слепок({узел, стили, титул, классТела}) собирает
     самодостаточный HTML из готового узла — им пользуется отчёт.
   ═══════════════════════════════════════════════════════════════════════ */
(function(){
  if(window.СЧХСохранить) return;

  /* ── 1. Стили. Значения — из канона .shm (report.html); палитра вшита
        числами, потому что окно живёт в body, вне корня страницы. ── */
  var CSS =
  '.ос{position:fixed;inset:0;z-index:90;display:none;align-items:center;justify-content:center;'+
  'padding:20px;min-width:320px;overflow:auto;'+
  "font-family:-apple-system,BlinkMacSystemFont,'SB Sans Text','Segoe UI',Roboto,Arial,sans-serif;"+
  'color:#1A1A1A;line-height:1.5;-webkit-font-smoothing:antialiased;text-align:center}'+
  '.ос.on{display:flex}'+
  'html.ос-стоп,html.ос-стоп body{overflow:hidden}'+
  '.ос,.ос *{box-sizing:border-box}'+
  '.ос-фон{position:fixed;inset:0;background:rgba(26,26,26,.55);'+
  'backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}'+
  '.ос-окно{position:relative;z-index:1;width:100%;max-width:500px;min-width:296px;margin:auto;'+
  'background:#fff;border-radius:20px;padding:34px 34px 30px;'+
  'box-shadow:0 18px 60px rgba(16,24,40,.28);outline:none}'+
  '.ос button.ос-крестик{position:absolute;top:14px;right:16px;z-index:2;width:34px;height:34px;'+
  'border:0;border-radius:12px;background:rgba(16,24,40,.05);color:#6B7280;'+
  'font-family:inherit;font-size:22px;line-height:1;cursor:pointer;transition:background .18s,color .18s}'+
  '.ос button.ос-крестик:hover{background:rgba(16,24,40,.09);color:#1A1A1A}'+
  /* заголовок и описание — как заголовок и слоган окна «Поделиться» */
  '.ос-заголовок{font-size:21px;font-weight:600;letter-spacing:-.02em;line-height:1.25;color:#4B5563;margin-bottom:8px}'+
  '.ос-описание{max-width:26em;margin:0 auto;font-size:13.5px;line-height:1.6;color:#6B7280}'+
  /* ряд плиток: стоят на месте, при наведении всплывает подпись */
  '.ос-ряд{display:flex;justify-content:center;align-items:flex-start;gap:16px;margin-top:26px}'+
  '.ос button.ос-знак{position:relative;display:flex;flex-direction:column;align-items:center;'+
  'width:44px;height:44px;padding:0;border:0;background:transparent;cursor:pointer;font-family:inherit}'+
  '.ос button.ос-знак svg{display:block;width:44px;height:44px;border-radius:14px;flex:none}'+
  '.ос button.ос-знак:active svg{opacity:.85}'+
  '.ос .ос-подпись{position:absolute;top:calc(100% + 9px);left:50%;transform:translateX(-50%) translateY(-4px);'+
  'padding:9px 13px;border-radius:12px;background:#fff;color:#1A1A1A;border:1px solid #E5E7EB;'+
  'font-size:12.5px;font-weight:600;white-space:nowrap;opacity:0;pointer-events:none;z-index:3;'+
  'box-shadow:0 8px 28px rgba(16,24,40,.16);transition:opacity .16s,transform .16s}'+
  '.ос button.ос-знак:hover .ос-подпись,.ос button.ос-знак:focus-visible .ос-подпись{opacity:1;transform:translateX(-50%)}'+
  /* без наведения (телефоны, планшеты) подписи стоят под плитками постоянно */
  '@media (hover:none){'+
  '.ос-ряд{gap:12px}'+
  '.ос button.ос-знак{width:auto;height:auto;flex:1 1 0;min-width:72px;max-width:110px}'+
  '.ос .ос-подпись{position:static;transform:none;opacity:1;padding:0;border:0;box-shadow:none;'+
  'background:none;white-space:normal;margin-top:8px;font-size:12px;font-weight:500;color:#6B7280;line-height:1.35}}'+
  '@media (max-width:600px){'+
  '.ос{padding:14px}.ос-окно{padding:28px 20px 26px}.ос-заголовок{font-size:19px}.ос-ряд{gap:12px}}'+
  '@media print{.ос{display:none!important}}';

  /* Плашка-уведомление — та же, что в отчёте и анкете (СЧХТост). Если на
     странице её нет (прайс), добавляем копию, чтобы сообщения выглядели одинаково. */
  var CSS_ТОСТ =
  '.schx-тосты{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:130;display:flex;'+
  'flex-direction:column;align-items:center;gap:8px;pointer-events:none;padding:0 12px;max-width:100%}'+
  '.schx-тост{display:flex;align-items:center;gap:11px;max-width:min(92vw,440px);padding:13px 18px;border-radius:14px;'+
  'background:rgba(255,255,255,.96);border:1px solid #E5E7EB;color:#374151;box-shadow:0 8px 28px rgba(16,24,40,.16);'+
  'backdrop-filter:blur(9px);-webkit-backdrop-filter:blur(9px);'+
  "font:13.5px/1.5 -apple-system,BlinkMacSystemFont,'SB Sans Text','Segoe UI',Roboto,Arial,sans-serif;"+
  'opacity:0;transform:translateY(12px);transition:opacity .22s ease,transform .22s ease}'+
  '.schx-тост.on{opacity:1;transform:none}'+
  '.schx-тост svg{width:20px;height:20px;flex:none;color:#1B9331}'+
  '.schx-тост.ошибка{background:#FFFBEF;border-color:#FBE3AE}'+
  '.schx-тост.ошибка svg{color:#F5B301}'+
  '.schx-действие{flex:none;margin-left:4px;padding:7px 12px;border:1px solid #E5E7EB;border-radius:12px;'+
  'background:#fff;color:#2A6FAB;cursor:pointer;'+
  "font:600 12.5px/1 -apple-system,BlinkMacSystemFont,'SB Sans Text','Segoe UI',Roboto,Arial,sans-serif;"+
  'transition:border-color .16s,color .16s}'+
  '.schx-действие:hover{border-color:#8FC7E8;color:#1D4ED8}';

  /* ── 2. Плитки: скруглённый квадрат 44×44 (viewBox 48), белый рисунок.
        «Скачать» — та же стрелка в лоток, что на кнопке меню (эталон
        report.html), зелёный фирменный; «Напечатать» — принтер, синий;
        «Отправить» — летящий конверт, фиолетовый. Цвета — из палитры
        отчёта (--c-g-500, --c-b-600, --c-v-700). ── */
  var ЗНАКИ = {
    'скачать':
      '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect width="48" height="48" rx="14" fill="#21A038"/>'+
      '<g transform="translate(12 12)"><path d="M12 3v12m0 0l-4.5-4.5M12 15l4.5-4.5" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'+
      '<path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="#fff" stroke-width="2.1" stroke-linecap="round"/></g></svg>',
    'печать':
      '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect width="48" height="48" rx="14" fill="#2F80C4"/>'+
      '<path d="M17 20v-6h14v6M17 34h14v-8H17v8Z" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'+
      '<path d="M17 30h-3v-8h20v8h-3" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    'отправить':
      '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect width="48" height="48" rx="14" fill="#6D3FD4"/>'+
      '<path d="M18 17.5h19a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" stroke="#fff" stroke-width="2.1" stroke-linejoin="round"/>'+
      '<path d="M16.6 19.6 27.5 27l10.9-7.4" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'+
      '<path d="M8.5 22h4.5M7 26h6M8.5 30h4.5" stroke="#fff" stroke-width="2.1" stroke-linecap="round"/></svg>'
  };
  var ПОДПИСИ = {'скачать':'Скачать файл','печать':'Напечатать или сохранить в PDF','отправить':'Отправить'};

  function xml(x){ return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function текст(x){ try{ return typeof x==='function' ? (x()||'') : (x||''); }catch(e){ return ''; } }
  function настройка(){ return window.СЧХДокумент || {}; }

  /* ── 3. Разметка — один раз, в body (вне корня страницы, как плашки). ── */
  var стиль=document.createElement('style'); стиль.id='ос-стиль';
  стиль.textContent = CSS + (window.СЧХТост ? '' : CSS_ТОСТ);
  document.head.appendChild(стиль);

  var окно=document.createElement('div'); окно.className='ос'; окно.id='окноСохранить';
  окно.innerHTML =
    '<div class="ос-фон" data-ос-закрыть></div>'+
    '<div class="ос-окно" role="dialog" aria-modal="true" aria-labelledby="осЗаголовок" tabindex="-1">'+
      '<button class="ос-крестик" type="button" data-ос-закрыть aria-label="Закрыть">×</button>'+
      '<div class="ос-заголовок" id="осЗаголовок">Сохранить документ</div>'+
      '<div class="ос-описание" id="осОписание"></div>'+
      '<div class="ос-ряд">'+
        ['скачать','печать','отправить'].map(function(к){
          return '<button type="button" class="ос-знак" data-ос="'+к+'" aria-label="'+xml(ПОДПИСИ[к])+'">'+
                 ЗНАКИ[к]+'<span class="ос-подпись">'+xml(ПОДПИСИ[к])+'</span></button>';
        }).join('')+
      '</div>'+
    '</div>';
  document.body.appendChild(окно);

  var диалог=окно.querySelector('.ос-окно');
  var заголовок=окно.querySelector('#осЗаголовок');
  var описание=окно.querySelector('#осОписание');
  var последний=null;
  function знак(к){ return окно.querySelector('[data-ос="'+к+'"]'); }

  /* ── 4. Открыть / закрыть ── */
  function заполнить(){
    var н=настройка();
    заголовок.textContent = текст(н.заголовок) || 'Сохранить документ';
    описание.textContent  = текст(н.описание);
    описание.style.display = описание.textContent ? '' : 'none';
    var естьФайл = typeof н.собратьФайл==='function';
    знак('скачать').style.display   = естьФайл ? '' : 'none';
    знак('отправить').style.display = естьФайл ? '' : 'none';
    знак('печать').style.display    = typeof н.напечатать==='function' ? '' : 'none';
  }
  function открыть(){
    заполнить();
    последний = document.activeElement;
    окно.classList.add('on');
    document.documentElement.classList.add('ос-стоп');
    setTimeout(function(){ try{ диалог.focus(); }catch(e){} }, 0);
  }
  function закрыть(){
    окно.classList.remove('on');
    document.documentElement.classList.remove('ос-стоп');
    if(последний && последний.focus){ try{ последний.focus(); }catch(e){} }
    последний=null;
  }
  окно.querySelectorAll('[data-ос-закрыть]').forEach(function(э){ э.onclick=закрыть; });
  document.addEventListener('keydown', function(e){
    if(e.key==='Escape' && окно.classList.contains('on')) закрыть();
  });

  /* ── 5. Плашка-уведомление ── */
  if(!window.СЧХТост){
    var ГАЛКА='<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4.5 12.5l5 5 10-11" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var ЗНАК ='<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 7.5v6M12 16.6v.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
    var короб=null;
    window.СЧХТост=function(т,вид,действие){
      if(!короб){ короб=document.createElement('div'); короб.className='schx-тосты';
        короб.setAttribute('role','status'); короб.setAttribute('aria-live','polite');
        document.body.appendChild(короб); }
      var э=document.createElement('div');
      э.className='schx-тост'+(вид?' '+вид:'');
      э.innerHTML=(вид==='ошибка'?ЗНАК:ГАЛКА)+'<span></span>';
      э.childNodes[1].textContent=т;
      if(действие && действие.текст){
        var к=document.createElement('button');
        к.type='button'; к.className='schx-действие'; к.textContent=действие.текст;
        к.onclick=function(){ убрать(); if(действие.делать) действие.делать(); };
        э.appendChild(к); э.style.pointerEvents='auto';
      }
      короб.appendChild(э);
      requestAnimationFrame(function(){ э.classList.add('on'); });
      function убрать(){ э.classList.remove('on'); setTimeout(function(){ if(э.parentNode) э.parentNode.removeChild(э); },300); }
      setTimeout(убрать, действие?6000:2600);
      return убрать;
    };
  }
  function тост(т,вид,действие){ window.СЧХТост(т,вид,действие); }

  /* ── 6. Файл документа ── */
  function имяФайла(){
    var н = текст(настройка().имяФайла) || document.title || 'Документ';
    return String(н).replace(/[\\/:*?"<>|]+/g,' ').replace(/\s+/g,' ').trim() + '.html';
  }
  function файл(){
    var н=настройка();
    if(typeof н.собратьФайл!=='function') return Promise.resolve(null);
    var р; try{ р=н.собратьФайл(); }catch(e){ р=null; }
    return Promise.resolve(р).then(function(х){ return (typeof х==='string' && х) ? х : null; }, function(){ return null; });
  }
  function скачать(html){
    var blob=new Blob([html],{type:'text/html;charset=utf-8'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob); a.download=имяФайла();
    document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); if(a.parentNode) a.parentNode.removeChild(a); }, 1500);
  }
  function письмо(){
    var п=настройка().письмо || {};
    var тема=текст(п.тема) || имяФайла().replace(/\.html$/,'');
    location.href='mailto:?subject='+encodeURIComponent(тема)+'&body='+encodeURIComponent(текст(п.текст));
  }
  var НЕТ_ФАЙЛА='Не удалось подготовить файл. Воспользуйтесь печатью и сохранением в PDF.';

  /* ── 7. Действия ── */
  function выполнить(что){
    var н=настройка();
    if(что==='печать'){
      закрыть();
      setTimeout(function(){ if(typeof н.напечатать==='function') н.напечатать(); else window.print(); }, 80);
      return;
    }
    if(что==='скачать'){
      файл().then(function(html){
        if(!html){ тост(НЕТ_ФАЙЛА,'ошибка'); return; }
        скачать(html); закрыть(); тост('Файл сохранён в загрузки');
      });
      return;
    }
    if(что==='отправить'){
      файл().then(function(html){
        if(!html){ тост(НЕТ_ФАЙЛА,'ошибка'); return; }
        var ф=null;
        try{ ф=new File([html], имяФайла(), {type:'text/html'}); }catch(e){}
        if(ф && navigator.canShare && navigator.canShare({files:[ф]})){
          var п=н.письмо||{};
          navigator.share({files:[ф], title:текст(п.тема)||имяФайла().replace(/\.html$/,''), text:текст(п.текст)||undefined})
            .then(закрыть, function(e){
              if(e && e.name==='AbortError') return;   /* человек передумал — ничего не делаем */
              запасной(html);
            });
          return;
        }
        запасной(html);
      });
    }
  }
  /* Нет системного окна «Поделиться» с файлами: файл — в загрузки, письмо — по кнопке */
  function запасной(html){
    скачать(html); закрыть();
    тост('Файл сохранён в загрузки — приложите его к письму или сообщению', null, {текст:'Написать письмо', делать:письмо});
  }
  окно.querySelectorAll('[data-ос]').forEach(function(б){
    б.onclick=function(){ выполнить(б.getAttribute('data-ос')); };
  });

  /* ── 8. Помощник: самодостаточный HTML из готового узла ── */
  function слепок(о){
    о=о||{};
    var узел=о.узел; var тело = узел ? (узел.outerHTML!==undefined ? узел.outerHTML : String(узел)) : '';
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8">'+
      '<meta name="viewport" content="width=device-width,initial-scale=1">'+
      '<title>'+xml(о.титул||document.title)+'</title>'+
      '<style>'+(о.стили||'')+'</style></head>'+
      '<body'+(о.классТела?' class="'+xml(о.классТела)+'"':'')+'>'+тело+'</body></html>';
  }

  window.СЧХСохранить=открыть;
  window.СЧХСохранить.закрыть=закрыть;
  window.СЧХСохранить.действие=выполнить;
  window.СЧХСохранить.имяФайла=имяФайла;
  window.СЧХСохранить.слепок=слепок;
})();
