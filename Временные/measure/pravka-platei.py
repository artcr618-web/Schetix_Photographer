from pathlib import Path
p=Path('/home/user/Schetix_Photographer/Веб/calc.html');s=p.read_text(encoding='utf-8')

for line in ['<div class="benefit-text">Соберёте график работы на&nbsp;неделю</div>\n',
             '<div class="benefit-text">Сформируете подробный прайс на&nbsp;свои услуги</div>\n',
             '<div class="benefit-text">Увидите, как вернутся вложения</div>\n']:
    assert s.count(line)==1, line[:40]
    s=s.replace(line,'')

старое_css='''#phc-root .benefit-text{font-size:12.5px;line-height:1.55;color:rgba(255,255,255,.76);
margin-bottom:6px}
/* Кнопка примера на трёх плашках шапки (18.09, слово владельца). Ведёт на
   preview.html — статический снимок отчёта по значениям по умолчанию:
   без анкетных данных, без формул, посетитель ничего не вводит. */
#phc-root .benefit-demo{margin-top:auto;flex:none;align-self:flex-start;display:inline-flex;
align-items:center;gap:7px;color:var(--c-white);font-size:12.5px;font-weight:600;
letter-spacing:-.01em;text-decoration:none;transition:.16s}
#phc-root .benefit-demo svg{width:14px;height:14px;flex:none;transition:transform .16s}
#phc-root .benefit-demo:hover{text-decoration:underline;text-underline-offset:3px}
#phc-root .benefit-demo:hover svg{transform:translateX(3px)}
#phc-root .benefit-demo:focus-visible{outline:2px solid var(--c-g-400);outline-offset:3px;border-radius:4px}'''
новое_css='''/* 18.09 (слово владельца): расшифровок под чёртой больше нет — на их месте
   ссылка на пример отчёта. Ведёт на preview.html: статический снимок отчёта
   по значениям по умолчанию, без анкетных данных и без формул. Набрана как
   обычный текст плашки — тот же кегль, межстрочный и цвет, без жирного. */
#phc-root .benefit-demo{flex:none;align-self:flex-start;display:inline-flex;align-items:center;
gap:6px;color:rgba(255,255,255,.76);font-size:12.5px;font-weight:400;line-height:1.55;
text-decoration:none;transition:.16s}
#phc-root .benefit-demo svg{width:13px;height:13px;flex:none;transition:transform .16s}
#phc-root .benefit-demo:hover{color:var(--c-white);text-decoration:underline;text-underline-offset:3px}
#phc-root .benefit-demo:hover svg{transform:translateX(3px)}
#phc-root .benefit-demo:focus-visible{outline:2px solid var(--c-g-400);outline-offset:3px;border-radius:4px}'''
assert s.count(старое_css)==1
s=s.replace(старое_css,новое_css)
p.write_text(s,encoding='utf-8')
print('готово; benefit-text осталось:',s.count('benefit-text'))
