#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает публикационный отчёт без development DEMO.

Источник разработки остаётся Веб/report.html. Артефакт Веб/Публикация/report.html уже имеет имя, под которым
его выгружают рядом с calc.html и price.html.
Он принимает только настоящий расчёт через ?data= или localStorage; прямое
открытие показывает путь к анкете, а не стартовые значения.

Запуск:
    python3 Инструменты/собрать_публикационный_отчёт.py
    python3 Инструменты/собрать_публикационный_отчёт.py --check
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Веб' / 'report.html'
TARGET = ROOT / 'Веб' / 'Публикация' / 'report.html'

EARLY_GUARD = '''<!-- PUBLICATION-ONLY: generated from report.html; do not edit directly. -->
<script>
/* До разбора body скрываем отчёт, если настоящий расчёт не был передан.
   Это не даёт статической разметке development-отчёта мелькнуть на экране. */
(function(){
  function read(){
    try{
      var q=location.search.match(/[?&]data=([^&]+)/);
      if(q){
        var byQuery=JSON.parse(decodeURIComponent(escape(atob(decodeURIComponent(q[1])))));
        if(byQuery&&typeof byQuery==='object')return byQuery;
      }
    }catch(e){}
    try{
      var raw=localStorage.getItem('phc_report');
      var byStorage=raw&&JSON.parse(raw);
      if(byStorage&&typeof byStorage==='object')return byStorage;
    }catch(e){}
    return null;
  }
  if(!read())document.documentElement.classList.add('phr-no-result');
})();
</script>
<style id="publication-no-result-style">
#publication-empty{display:none;min-height:100vh;padding:32px 16px;
  align-items:center;justify-content:center;background:#F6F7F8;
  color:#202124;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
html.phr-no-result #phr-root,html.phr-no-result .shm,html.phr-no-result .thxm{display:none!important}
html.phr-no-result #publication-empty{display:flex}
#publication-empty .publication-empty-card{width:min(100%,620px);padding:36px;
  border:1px solid #E5E7EB;border-radius:20px;background:#FFF;box-shadow:0 8px 28px rgba(16,24,40,.08);text-align:center}
#publication-empty h1{margin:0 0 12px;font-size:clamp(25px,4vw,36px);line-height:1.15;letter-spacing:-.025em}
#publication-empty p{margin:0;color:#667085}
#publication-empty .publication-empty-action{display:inline-flex;align-items:center;justify-content:center;margin-top:24px;
  min-height:48px;padding:0 20px;border-radius:12px;background:#1B9331;color:#FFF;text-decoration:none;font-weight:700}
#publication-empty .publication-empty-action:hover{background:#147B28}
</style>
'''

EMPTY_STATE = '''<main id="publication-empty" role="main" aria-labelledby="publication-empty-title">
  <section class="publication-empty-card">
    <h1 id="publication-empty-title">Сначала рассчитайте свою ставку</h1>
    <p>Этот отчёт формируется только по результату заполненной анкеты. Вернитесь в калькулятор, заполните данные — и мы покажем ваш персональный результат.</p>
    <a class="publication-empty-action" href="calc.html">Заполнить анкету</a>
  </section>
</main>
'''


def object_end(text: str, start: int) -> int:
    """Возвращает индекс закрывающей точки с запятой после JS-объекта."""
    brace = text.find('{', start)
    if brace < 0:
        raise ValueError('после var DEMO не найден объект')
    depth = 0
    quote = ''
    escaped = False
    for index in range(brace, len(text)):
        ch = text[index]
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                quote = ''
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                semi = index + 1
                if semi >= len(text) or text[semi] != ';':
                    raise ValueError('DEMO-объект должен заканчиваться точкой с запятой')
                return semi + 1
    raise ValueError('DEMO-объект не закрыт')


def publication_source(source: str) -> str:
    demo = source.find('var DEMO=')
    if demo < 0:
        raise ValueError('в development report.html не найден var DEMO')
    comment = source.rfind('/* ДЕМО-НАБОР.', 0, demo)
    if comment < 0:
        raise ValueError('перед DEMO не найден ожидаемый маркер')
    source = (source[:comment]
              + '/* Публикационная сборка не содержит технический DEMO-набор. */\n'
              + source[object_end(source, demo):])
    if 'return DEMO;' not in source:
        raise ValueError('в loadData не найдено возвращение DEMO')
    source = source.replace(
        '''  /* Расчёта нет — показываем расчёт по значениям анкеты по умолчанию.
     Это не выдуманные числа: набор пересобирается скриптом части/демо.py
     из настоящего calc(), и проверка следит, чтобы они совпадали. */
  return DEMO;''',
        '''  /* В публикации прямой отчёт без результата не подменяем DEMO-набором. */
  return null;''',
        1,
    )
    marker = 'var d=loadData();'
    if marker not in source:
        raise ValueError('не найдено присваивание d=loadData()')
    source = source.replace(marker, marker + '''
/* Без результата останавливаем рендер отчёта. Ранний guard в <head> уже
   скрыл разметку; здесь задаём явный публичный мост для поздних скриптов. */
if(!d){
  document.documentElement.classList.add('phr-no-result');
  var publicationRoot=document.getElementById('phr-root');
  if(publicationRoot)publicationRoot.hidden=true;
  window.PHR_D=null;
  return;
}''', 1)
    if '<head>' not in source or '<div id="phr-root"' not in source:
        raise ValueError('не найдены точки вставки публикационной оболочки')
    source = source.replace('<head>', '<head>\n' + EARLY_GUARD, 1)
    source = source.replace('<div id="phr-root"', EMPTY_STATE + '<div id="phr-root"', 1)
    if 'var DEMO=' in source or 'return DEMO;' in source:
        raise ValueError('в публикационном отчёте остался исполняемый DEMO')
    digest = hashlib.sha256((ROOT / 'Веб' / 'report.html').read_bytes()).hexdigest()
    banner = f'<!-- GENERATED: source=Веб/report.html sha256={digest}; command=python3 Инструменты/собрать_публикационный_отчёт.py -->\n'
    return banner + source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='не писать файл, а проверить актуальность сборки')
    args = parser.parse_args()
    generated = publication_source(SOURCE.read_text(encoding='utf-8'))
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding='utf-8') != generated:
            raise SystemExit('публикационный отчёт не синхронен: запустите python3 Инструменты/собрать_публикационный_отчёт.py')
        print('публикационный отчёт синхронен:', TARGET.relative_to(ROOT))
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(generated, encoding='utf-8')
    print('публикационный отчёт собран:', TARGET.relative_to(ROOT))


if __name__ == '__main__':
    main()
