from pathlib import Path
p=Path('/home/user/Schetix_Photographer/Веб/calc.html');s=p.read_text(encoding='utf-8')

старое='''#phc-root .benefit-title{display:flex;align-items:flex-end;flex:none;width:100%;height:94px;
font-family:'PHC Prata','Times New Roman',serif;font-size:24px;font-weight:400;
letter-spacing:-.02em;line-height:1.2;margin:18px 0 12px;padding-bottom:12px;
color:var(--c-white);border-bottom:1px solid rgba(255,255,255,.24)}'''
новое='''/* 18.09 (слово владельца): композиция трёх плашек. За дефолт — зазор
   первой плашки — 38 px от иконки до текста; теперь он одинаков у всех трёх.
   Текст прибит к верху (align-items:flex-start), а место под ним зарезервировано
   под три строки заголовка (min-height 99), поэтому разделительная черта лежит
   на одной высоте и у двухстрочных, и у трёхстрочных заголовков: средняя
   плашка больше не поднимает текст к иконке, когда строка переносится. */
#phc-root .benefit-title{display:flex;align-items:flex-start;flex:none;width:100%;min-height:99px;
font-family:'PHC Prata','Times New Roman',serif;font-size:24px;font-weight:400;
letter-spacing:-.02em;line-height:1.2;margin:38px 0 12px;padding-bottom:12px;
color:var(--c-white);border-bottom:1px solid rgba(255,255,255,.24)}'''
assert s.count(старое)==1
s=s.replace(старое,новое)

# мобильная разметка остаётся как есть: там плашки в столбик и черта идёт
# плотно под текстом, резерв под три строки им не нужен
м='''#phc-root .benefit-title{height:auto;align-items:flex-start;margin-top:18px}'''
н='''#phc-root .benefit-title{height:auto;min-height:0;align-items:flex-start;margin-top:18px}'''
assert s.count(м)==1
s=s.replace(м,н)
p.write_text(s,encoding='utf-8')
print('готово')
