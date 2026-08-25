# -*- coding: utf-8 -*-
"""Встраивает справочник и всплывающие подсказки в анкету calc.html.

Источник правды — словарь СПРАВОЧНИК из части/таблицы_прототип.py, тот же,
что уходит в отчёт. Здесь он вставляется в анкету между метками
<!--СПРАВОЧНИК-НАЧАЛО--> и <!--СПРАВОЧНИК-КОНЕЦ--> вместе со скриптом,
который подчёркивает знакомые слова в вопросах и показывает определение.

Запуск: python3 части/подсказки.py
"""
import io, json, re, runpy

КОРЕНЬ = '/home/user/schetix'
нс = runpy.run_path(КОРЕНЬ + '/Инструменты/таблицы_прототип.py')
СПРАВОЧНИК = нс['СПРАВОЧНИК']

# какие слова подсвечиваем: запись справочника → образец поиска в тексте
# В JavaScript \w — только латиница, поэтому окончания задаём явным
# классом кириллических букв.
СЛОВА = {
    # Пробел пишем явным классом, а не \\s: обратная косая при переносе
    # в JavaScript теряется, и образец переставал работать.
    'Амортизация':            'амортизаци[а-яё]*',
    'Срок службы':            'срок[а-яё]*[ ]+службы',
    'Эквайринг':              'эквайринг[а-яё]*',
    'Постпродакшн':           'постпродакшн[а-яё]*',
    'Первичная обработка':    'первичн[а-яё]+[ ]+обработк[а-яё]+',
    'Готовые кадры':          'готов[а-яё]+[ ]+кадр[а-яё]*',
    'Срабатывание затвора':   'срабатыван[а-яё]+[ ]+затвора',
    'Ресурс затвора':         'ресурс[а-яё]*[ ]+затвора',
    'Съёмочное оборудование': 'съёмочн[а-яё]+[ ]+оборудован[а-яё]+',
    'Офисное оборудование':   'офисн[а-яё]+[ ]+оборудован[а-яё]+',
    'Подписки':               'подписк[а-яё]+',
    'Проектное время':        'проектн[а-яё]+[ ]+врем[а-яё]+',
    'Рабочее время':          'рабоч[а-яё]+[ ]+врем[а-яё]+',
    'Рабочие паузы':          'рабоч[а-яё]+[ ]+пауз[а-яё]+',
    'Резерв времени на форс-мажоры': 'форс-мажор[а-яё]*',
    'Резерв на развитие':     'фонд[а-яё]*[ ]+развития',
    'Запас на скидку':        'запас[а-яё]*[ ]+на[ ]+скидку',
    'Налоговый режим':        'налогов[а-яё]+[ ]+режим[а-яё]*',
    'Страховые взносы':       'страхов[а-яё]+[ ]+взнос[а-яё]+',
    'Точка безубыточности':   'точк[а-яё]+[ ]+безубыточности',
    'Доход на руки':          'доход[а-яё]*[ ]+на[ ]+руки',
    'Выручка':                'выручк[а-яё]+',
    'Логистика':              'логистик[а-яё]+',
    'Поиск заказов':          'поиск[а-яё]*[ ]+заказов',
    'Проектная работа с клиентами': 'работ[а-яё]+[ ]+с[ ]+клиентом',
    'Отчётность':             'отчётност[а-яё]+',
    'Бухгалтерия':            'бухгалтери[а-яё]+',
    'Продвижение':            'продвижени[а-яё]+',
    'Реклама':                'реклам[а-яё]+',
    'Обучение':               'обучени[а-яё]+',
    'Минимальный выезд':      'минимальн[а-яё]+[ ]+выезд[а-яё]*',
    'Учёт':                   'учёт[а-яё]*',
    'Сайт':                   'сайт[а-яё]*',
    'Юнит-экономика':         'юнит-экономик[а-яё]*',
}
нужные = {т: СПРАВОЧНИК[т] for т in СЛОВА if т in СПРАВОЧНИК}
нет = [т for т in СЛОВА if т not in СПРАВОЧНИК]
if нет:
    raise SystemExit('нет таких записей в справочнике: ' + ', '.join(нет))

БЛОК = '''<!--СПРАВОЧНИК-НАЧАЛО-->
<style>
/* Подсказка по справочнику: пунктир под словом, определение по наведению.
   Вид тот же, что у подсказок в отчёте: белая плашка, рамка 1px,
   тень 0 8px 28px, появление за 0,16 с. */
#phc-root .спр-слово{border-bottom:1px dotted var(--c-gr2);cursor:help;position:relative}
#phc-root .спр-слово:after{content:attr(data-опис);position:absolute;left:0;top:calc(100%% + 8px);
z-index:60;width:max-content;max-width:340px;padding:11px 14px;border-radius:12px;background:#fff;
color:var(--c-ink2);border:1px solid var(--c-ln);font-size:12.5px;font-weight:400;line-height:1.5;
text-align:left;white-space:normal;opacity:0;pointer-events:none;
box-shadow:0 8px 28px rgba(16,24,40,.16);transform:translateY(-4px);
transition:opacity .16s,transform .16s}
#phc-root .спр-слово:before{content:attr(data-имя);position:absolute;left:0;top:calc(100%% + 8px);
z-index:61;padding:11px 14px;font-size:12.5px;font-weight:700;color:var(--c-ink);
opacity:0;pointer-events:none;transition:opacity .16s}
#phc-root .спр-слово:hover:after,#phc-root .спр-слово.открыта:after{opacity:1;transform:translateY(0)}
@media(max-width:700px){#phc-root .спр-слово:after{max-width:260px}}
</style>
<script>
(function(){
  var СПР=%(данные)s, СЛОВА=%(слова)s;
  var корень=document.getElementById('phc-root'); if(!корень)return;
  /* Ждём, пока анкета достроит свои блоки и обновит склонения:
     иначе её код перезапишет разметку вместе с нашими подсказками. */
  function разметить(){
  /* Ищем только в вопросах и пояснениях: в поля ввода и кнопки не лезем. */
  var где='h2,.q,.qd,.hint,.def,.note,.section-subtitle';
  var найдено={};
  корень.querySelectorAll(где).forEach(function(эл){
    if(эл.closest('input,textarea,button'))return;
    Object.keys(СЛОВА).forEach(function(термин){
      if(найдено[термин])return;                 /* один раз на всю анкету */
      var re=new RegExp('('+СЛОВА[термин]+')','i');
      var узлы=[], хд=document.createTreeWalker(эл,NodeFilter.SHOW_TEXT,null);
      while(хд.nextNode())узлы.push(хд.currentNode);
      for(var i=0;i<узлы.length;i++){
        var t=узлы[i], m=re.exec(t.nodeValue);
        if(!m)continue;
        if(t.parentNode.classList&&t.parentNode.classList.contains('спр-слово'))continue;
        var сп=document.createElement('span');
        сп.className='спр-слово'; сп.tabIndex=0;
        сп.setAttribute('data-имя',термин);
        сп.setAttribute('data-опис',термин+' — '+СПР[термин]);
        сп.textContent=m[0];
        var хвост=t.splitText(m.index);
        хвост.nodeValue=хвост.nodeValue.slice(m[0].length);
        t.parentNode.insertBefore(сп,хвост);
        найдено[термин]=1;
        break;
      }
    });
  });
  }
  if(document.readyState==='complete')setTimeout(разметить,0);
  else window.addEventListener('load',function(){setTimeout(разметить,0)});

  /* На телефоне наведения нет: показываем по нажатию, закрываем по второму. */
  корень.addEventListener('click',function(с){
    var сл=с.target.closest&&с.target.closest('.спр-слово');
    корень.querySelectorAll('.спр-слово.открыта').forEach(function(э){
      if(э!==сл)э.classList.remove('открыта');
    });
    if(сл)сл.classList.toggle('открыта');
  });
})();
</script>
<!--СПРАВОЧНИК-КОНЕЦ-->''' % {'данные': json.dumps(нужные, ensure_ascii=False),
                              'слова': json.dumps(СЛОВА, ensure_ascii=False)}

путь = КОРЕНЬ + '/Веб/calc.html'
s = io.open(путь, encoding='utf-8').read()
if '<!--СПРАВОЧНИК-НАЧАЛО-->' in s:
    s = re.sub(r'<!--СПРАВОЧНИК-НАЧАЛО-->.*?<!--СПРАВОЧНИК-КОНЕЦ-->', БЛОК, s, flags=re.S)
elif '</body>' in s:
    s = s.replace('</body>', БЛОК + '\n</body>', 1)
else:                       # анкета — фрагмент страницы, тега body в ней нет
    s = s.rstrip('\n') + '\n\n' + БЛОК + '\n'
io.open(путь, 'w', encoding='utf-8').write(s)
print('подсказки встроены, слов:', len(нужные))
