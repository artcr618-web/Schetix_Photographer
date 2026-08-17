#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Оптимизация web/calc.html. Читает оригинал, пишет копию.
   python3 оптимизация.py [исходник] [результат]
Ничего не выдумывает: только убирает мёртвое и дублирующееся
и снимает лишние пересчёты. Каждый шаг печатает, что сделал."""
import re, io, sys, collections

ВХОД  = sys.argv[1] if len(sys.argv) > 1 else '/home/user/schetix/web/calc.html'
ВЫХОД = sys.argv[2] if len(sys.argv) > 2 else '/home/user/эксперимент/web/calc.html'
s = io.open(ВХОД, encoding='utf-8').read()
было = len(s)
отчёт = []

# ─────────────────────────────────────── 1. МЁРТВЫЙ CSS
css_m = re.search(r'(<style[^>]*>)([\s\S]*?)(</style>)', s)
css = css_m.group(2)
разметка = re.sub(r'<style[\s\S]*?</style>|<script[\s\S]*?</script>', '', s)
js = '\n'.join(re.findall(r'<script[^>]*>([\s\S]*?)</script>', s))

живые = set(w for a in re.findall(r'class="([^"]+)"', разметка) for w in a.split())
живые |= set(w for a in re.findall(r"class=[\\]?['\"]([^'\"\\]+)", js) for w in a.split())
живые |= set(re.findall(r"classList\.[a-z]+\(['\"]([\w-]+)", js))
живые |= set(re.findall(r"querySelector(?:All)?\(['\"][^'\"]*[.\[]([\w-]+)", js))
живые |= set(re.findall(r"className\s*=\s*['\"]([^'\"]+)", js))
живые |= set(re.findall(r"\.contains\(['\"]([\w-]+)", js))
# всё, что вообще встречается в JS как отдельное слово в кавычках
живые |= set(re.findall(r"['\"]([a-z][\w-]{2,})['\"]", js))

# Классы, которые код собирает из кусков: 'dmc d'+номер, 'loyc g'+номер,
# 'scn3 '+вариант. Ни один из них не встречается в файле целиком, поэтому
# любую чистку «по факту употребления» они не переживут. Собираем префиксы
# и защищаем всё, что из них может получиться.
префиксы = set()
for m in re.finditer(r'''class=\\?["']([^"'\\]*?)\\?["']\s*\+''', js):
    хвост = m.group(1).strip().split(' ')[-1]
    if хвост: префиксы.add(хвост)
for m in re.finditer(r'''classList\.[a-z]+\(\s*['"]([\w-]*?)['"]\s*\+''', js):
    if m.group(1): префиксы.add(m.group(1))

def разобрать(css):
    """список (контекст, полный_текст_правила, селектор) с учётом @media"""
    из = []
    i = 0; n = len(css)
    while i < n:
        # блок @media
        m = re.compile(r'@[\w-]+[^{]*\{').search(css, i)
        r = re.compile(r'([^{}@]+)\{([^{}]*)\}').search(css, i)
        if m and (not r or m.start() < r.start()):
            # найти парную скобку
            гл = 1; p = m.end()
            while p < n and гл:
                if css[p] == '{': гл += 1
                elif css[p] == '}': гл -= 1
                p += 1
            внутри = css[m.end():p-1]
            вложенные = разобрать(внутри)
            из.append(('media', css[m.start():p], m.group(0), вложенные))
            i = p
        elif r:
            из.append(('rule', css[r.start():r.end()], r.group(1), None))
            i = r.end()
        else:
            хвост = css[i:]
            if хвост.strip(): из.append(('text', хвост, '', None))
            break
    return из

def динамический(к):
    return any(к.startswith(п) and к != п and к[len(п):].isdigit() for п in префиксы)

def мёртвое(сел):
    классы = set(re.findall(r'\.([\w-]+)', сел))
    if not классы: return False
    if any(динамический(к) for к in классы): return False
    return not (классы & живые)

def чистить(узлы, счёт):
    вых = []
    for тип, текст, сел, дети in узлы:
        if тип == 'rule':
            if мёртвое(сел): счёт[0] += 1; счёт[1] += len(текст); continue
            вых.append(текст)
        elif тип == 'media':
            внутр = чистить(дети, счёт)
            if not внутр.strip(): счёт[2] += 1; continue
            вых.append(сел + внутр + '}')
        else:
            вых.append(текст)
    return ''.join(вых)

счёт = [0, 0, 0]
новый_css = чистить(разобрать(css), счёт)
отчёт.append(f'мёртвых CSS-правил удалено: {счёт[0]} (≈{счёт[1]/1024:.1f} КБ), опустевших медиаблоков: {счёт[2]}')

# ─────────────────────────────────────── 2. ДУБЛЬ .wk .hr
дубль = '#phc-root .wk .hr{font-size:10px;color:var(--c-ln);text-align:right;padding-right:6px;line-height:15px}'
if дубль in новый_css:
    новый_css = новый_css.replace(дубль + '\n', '').replace(дубль, '')
    отчёт.append('убрано перекрытое правило .wk .hr (задавалось дважды подряд, работало только второе)')

s = s[:css_m.start(2)] + новый_css + s[css_m.end(2):]

# ─────────────────────────────────────── 3. ЛИШНИЕ ПЕРЕСЧЁТЫ НА ПРОКРУТКЕ
старое_scroll = "window.addEventListener('scroll',function(){лимит()},{passive:true});"
новое_scroll = """/* На прокрутке данные не меняются — пересчитывать модель незачем.
   Полосе нужно лишь знать, видно ли блок режима на экране, поэтому
   здесь только показ, а сам расчёт идёт из recalc(). Ещё и раз в кадр:
   событие scroll приходит десятки раз в секунду. */
var _полосаЖдёт=false;
window.addEventListener('scroll',function(){
  if(_полосаЖдёт)return;
  _полосаЖдёт=true;
  (window.requestAnimationFrame||setTimeout)(function(){_полосаЖдёт=false;полоса()},16);
},{passive:true});"""
if старое_scroll in s:
    s = s.replace(старое_scroll, новое_scroll)
    отчёт.append('прокрутка больше не запускает пересчёт модели: только показ полосы, не чаще раза в кадр')

# ─────────────────────────────────────── 4. КЭШ РЕЗУЛЬТАТА calc()
старый_вход = "function calc(){\n  var promo="
новый_вход = """/* Результат расчёта живёт до следующей правки данных. За один ввод
   calc() зовут и recalc(), и лимит(), и подобрать() — раньше модель
   считалась по пять-шесть раз подряд на одних и тех же значениях. */
var _кэш=null;
function сброситьКэш(){_кэш=null}
function calc(){
  if(_кэш)return _кэш;
  return _кэш=посчитать();
}
function посчитать(){
  var promo="""
if старый_вход in s:
    s = s.replace(старый_вход, новый_вход)
    # сбрасывать кэш при любом изменении данных
    s = s.replace("function recalc(){", "function recalc(){\n  сброситьКэш();", 1)
    # подобрать() перебирает режимы, меняя select — кэш обязан сбрасываться на каждом шаге
    s = s.replace("    sel.value=rg;\n    var d; try{ d=calc() }catch(e){ return }",
                  "    sel.value=rg;\n    сброситьКэш();\n    var d; try{ d=calc() }catch(e){ return }")
    s = s.replace("  sel.value=лучший;\n  if(лучший!==было", "  sel.value=лучший;\n  сброситьКэш();\n  if(лучший!==было")
    # кнопка расчёта и сохранение обязаны видеть свежие данные
    s = s.replace("$('go').onclick=function(){\n  var d=calc();", "$('go').onclick=function(){\n  сброситьКэш();\n  var d=calc();")
    s = s.replace("      var res=calc();", "      сброситьКэш();\n      var res=calc();")
    отчёт.append('добавлен кэш расчёта: за одно изменение модель считается один раз вместо пяти-шести')

# ─────────────────────────────────────── 5. ДУБЛЬ СНИМКА СТРОК
дубль_снимка = """var СТРОК_БЫЛО_КАРТ={};
Object.keys(CAT).forEach(function(f){
  var tb=$('t_'+f); if(tb)СТРОК_БЫЛО_КАРТ[f]=tb.querySelectorAll('tr').length;
});"""
if дубль_снимка in s:
    s = s.replace(дубль_снимка, 'var СТРОК_БЫЛО_КАРТ=СТРОК_БЫЛО;   /* тот же снимок, второе имя для читаемости */')
    отчёт.append('снимок числа строк собирался дважды подряд в две переменные — теперь один')

io.open(ВЫХОД, 'w', encoding='utf-8').write(s)
стало = len(s)
print('\n'.join('  • ' + х for х in отчёт))
print(f'\n  размер: {было/1024:.0f} КБ → {стало/1024:.0f} КБ  (−{(было-стало)/1024:.0f} КБ, −{(было-стало)/было*100:.0f}%)')
