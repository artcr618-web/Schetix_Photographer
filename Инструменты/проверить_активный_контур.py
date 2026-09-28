#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Зелёный гейт исполняемого веб-контура «Счётикса». 

Проверяет только активную цепочку calc → report / price (обложка index.html
удалена из репозитория 28.09). Книга, архив, PDF и Веб/Части не читаются.
Исторический аудит `--legacy` и скрипты синхронизации книги удалены 28.09
по решению владельца.

Запуск:
    python3 Инструменты/проверить_активный_контур.py [корень]
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]).resolve()
TOOLS = ROOT / 'Инструменты'
NODE = 'node'
ok, fail = [], []


def check(name, condition, detail=''):
    (ok if condition else fail).append((name, detail))


def command(args, *, cwd=None, timeout=180):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def harness(override=None):
    result = command([NODE, str(TOOLS / 'харнесс.js'), str(ROOT),
                      json.dumps(override or {}, ensure_ascii=False)])
    if result.returncode or not result.stdout.strip():
        raise RuntimeError((result.stderr or result.stdout or 'пустой вывод').strip()[:300])
    return json.loads(result.stdout)


def js_syntax(page):
    source = (ROOT / 'Веб' / page).read_text(encoding='utf-8')
    scripts = re.findall(r'<script[^>]*>[\s\S]*?</script>', source)
    javascript = '\n'.join(re.sub(r'^<script[^>]*>|</script>$', '', block.strip(), flags=re.S)
                           for block in scripts)
    with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as temp:
        temp.write(javascript)
        filename = temp.name
    try:
        result = command([NODE, '--check', filename])
        return result.returncode == 0, (result.stderr or result.stdout).strip()[:200]
    finally:
        os.unlink(filename)


def main():
    print('▶ активный веб-контур')
    active_files = ('index.html', 'calc.html', 'report.html', 'price.html')
    check('активные HTML-страницы существуют',
          all((ROOT / 'Веб' / page).is_file() for page in active_files))
    check('инструменты канонического default существуют',
          (TOOLS / 'проверить_calc_browser_default.js').is_file()
          and (TOOLS / 'харнесс.js').is_file()
          and (TOOLS / 'проверить_report_headless.js').is_file())
    check('публикационная сборка отчёта существует в отдельной папке',
          (ROOT / 'Веб' / 'Публикация' / 'report.html').is_file()
          and not (ROOT / 'Веб' / 'report.public.html').exists()
          and (TOOLS / 'собрать_публикационный_отчёт.py').is_file()
          and (TOOLS / 'проверить_публикационный_отчёт.js').is_file())

    jsdom = command([NODE, '-e', 'require.resolve("jsdom")'], cwd=TOOLS)
    if jsdom.returncode:
        install = command(['npm', 'ci', '--ignore-scripts', '--silent'], cwd=TOOLS, timeout=900)
        check('jsdom доступен для browser/headless-гейтов', install.returncode == 0,
              (install.stderr or install.stdout).strip().split('\n')[-1][:180])
    else:
        check('jsdom доступен для browser/headless-гейтов', True)
    if fail:
        finish()
        return

    preview_build = command([NODE, str(TOOLS / 'снять_preview.js'), str(ROOT)], cwd=TOOLS, timeout=180)
    check('статический preview.html пересобирается из development DEMO', preview_build.returncode == 0,
          (preview_build.stderr or preview_build.stdout).strip().split('\n')[-1][:200])

    for page in active_files:
        valid, detail = js_syntax(page)
        check(f'{page}: inline JavaScript компилируется', valid, detail)
    valid, detail = js_syntax('Публикация/report.html')
    check('Публикация/report.html: inline JavaScript компилируется', valid, detail)

    calc_source = (ROOT / 'Веб' / 'calc.html').read_text(encoding='utf-8')
    price_source = (ROOT / 'Веб' / 'price.html').read_text(encoding='utf-8')
    report_source = (ROOT / 'Веб' / 'report.html').read_text(encoding='utf-8')
    preview_path = ROOT / 'Веб' / 'preview.html'
    preview_source = preview_path.read_text(encoding='utf-8') if preview_path.is_file() else ''
    # 28.09: внешние ресурсы страниц (<script src>, <img src>, url('IMG/…')) обязаны
    # существовать рядом со страницей. Эта проверка ловит, например, перенос
    # Tools/printPage.js, после которого весь основной скрипт прайса падал.
    missing = []
    for page in active_files + ('Публикация/report.html',):
        path = ROOT / 'Веб' / page
        source = path.read_text(encoding='utf-8')
        refs = re.findall(r'<script[^>]+src="([^"]+)"', source)
        refs += re.findall(r'<img[^>]+src="([^"#]+)"', source)
        refs += re.findall(r"url\('((?:IMG|Fonts)/[^']+)'\)", source)
        # пути, записанные в скрипте строкой (например, CHARACTERS в report.html)
        refs += re.findall(r"['\"]((?:IMG|Fonts|Tools)/[^'\"\s]+\.(?:png|jpe?g|webp|svg|gif|ttf|woff2?|js))['\"]", source)
        for ref in refs:
            # адрес, собираемый в скрипте ('+…+'), проверяется строкой выше
            if re.match(r'^(https?:|data:|/cdn-cgi/|//)', ref) or "'+" in ref:
                continue
            # Публикационную копию выкладывают рядом с calc.html и price.html
            # (вместо development report), поэтому её пути считаются от Веб/.
            base = ROOT / 'Веб'
            if not (base / ref).is_file():
                missing.append(f'{page} → {ref}')
    check('внешние ресурсы страниц существуют', not missing, '; '.join(missing)[:240])

    check('активные локальные переходы ведут к существующим целям',
          calc_source.count('href="preview.html"') == 3
          and calc_source.count('>Посмотреть пример отчёта<') == 3
          and preview_path.is_file()
          and '<script' not in preview_source.lower()
          and 'href="report.html#detailing"' not in price_source
          and 'href="report.html#спрдет"' in price_source
          and 'id="спрдет"' in report_source,
          'preview.html, его статичность или якорь детализации')

    contract = command([sys.executable, str(TOOLS / 'проверить_контракт_d.py'), str(ROOT)])
    check('контракт d: calc, report и price используют согласованную схему',
          contract.returncode == 0, (contract.stderr or contract.stdout).strip().split('\n')[-1][:200])

    browser = command([NODE, str(TOOLS / 'проверить_calc_browser_default.js'), str(ROOT),
                       '--assert', '--check-demo', '--check-price-demo', '--result'], cwd=TOOLS)
    check('browser-default: golden snapshot, report DEMO и price DEMO совпадают',
          browser.returncode == 0, (browser.stderr or browser.stdout).strip().split('\n')[-1][:200])
    # Публикационная копия существует и уже проверена выше на синтаксис, но
    # намеренно не синхронизируется при правках development-отчёта: владелец
    # отдельно запрещает начинать фактическую подготовку публикации без команды.
    # Поэтому её content-gate (который требует пересборки) не входит в active.
    browser_data = None
    try:
        browser_data = json.loads(browser.stdout)
    except Exception as error:
        check('browser-default: результат d читается как JSON', False, str(error)[:160])

    try:
        base = harness()
        parts = base.pop('__parts')
        same = browser_data is not None and json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(',', ':')) == \
               json.dumps(browser_data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        check('харнесс: пустой сценарий равен реальному browser-default', same,
              'разные объекты d' if not same else '')
        check('расчёт: сумма сегментов отчёта равна выручке',
              abs(sum(parts) - base['R']) < 1,
              f"Δ={sum(parts)-base['R']:.6f}")
        check('расчёт: выручка раскладывается на расходы, налоги, фонды и цель',
              abs(base['R'] - base['C'] - base['aq'] - base['taxAll'] - base['fundY']
                  - base['discY'] - base['Ny']) < 1,
              f"R={base['R']:.2f}")
        check('расчёт: browser-default включает управление и все резервы, автофонд и автоматически подобранный УСН',
              base['mgmtT'] > 0 and base['fmT'] > 0 and base['discP'] == .15
              and base['varEmp'] == 0 and base['fundP'] > 0 and base['regimeCode'] == 'usn6',
              f"mgmtT={base['mgmtT']}; fmT={base['fmT']}; discP={base['discP']}; varEmp={base['varEmp']}; fundP={base['fundP']}; regime={base['regimeCode']}")
        check('З-001: чистая прибыль и буфер явно складываются в совместимый fundY',
              abs(base['fundY'] - base['profitY'] - base['cushionY']) < 1e-7,
              f"fundY={base['fundY']}; profitY={base['profitY']}; cushionY={base['cushionY']}")
        check('З-001: инвестиционная витрина и срок возврата считаются в calc()',
              abs(base['investmentTotal'] - base['investmentShoot'] - base['investmentPost']
                  - base['investmentTime']) < 1e-7
              and base['profitY'] > 0
              and abs(base['investmentPaybackYears'] - base['investmentTotal'] / base['profitY']) < 1e-9,
              f"вложения={base['investmentTotal']}; срок={base['investmentPaybackYears']}")
        check('З-001: износ съёмочного комплекта передаётся готовым на срабатывание',
              abs(base['shootEquipmentWear'] - base['depShoot'] / base['shotsYear']) < 1e-12,
              f"износ={base['shootEquipmentWear']}")
        check('З-055: прямые расходы на кадр передаются готовой суммой calc()',
              abs(base['directFrameCosts'] - (base['depShoot'] + base['depOffice'] + base['depSoft']
                  + base['varSoft'] + base['depWs'] + base['varRent'])) < 1e-12,
              f"прямые={base['directFrameCosts']}")
        check('З-001: запас выручки до точки безубыточности — точная доля текущей выручки',
              base['Rc'] > 0 and abs(base['currentBreakEvenMargin'] - (base['Rc'] - base['Rb']) / base['Rc']) < 1e-12,
              f"запас={base['currentBreakEvenMargin']}")
    except Exception as error:
        check('харнесс: пустой сценарий и базовые инварианты выполняются', False, str(error)[:200])

    try:
        employee = harness({'CAT': {'Form024': {'k': 'per', 'rows': [['Помощник', 30000, 12]]}},
                            'EXC_ВНЕШ': {'Form024': False}})
        check('сотрудники: 30 000 ₽ × 12 попадают в varEmp и последний сектор',
              employee['varEmp'] == 360000 and len(employee['__parts']) == 19
              and employee['__parts'][18] == 360000,
              f"varEmp={employee['varEmp']}; parts={len(employee['__parts'])}")
        check('сотрудники: структура отчёта не теряет и не дублирует сумму',
              abs(sum(employee['__parts']) - employee['R']) < 1,
              f"Δ={sum(employee['__parts'])-employee['R']:.6f}")
    except Exception as error:
        check('сотрудники: сценарий расчёта выполняется', False, str(error)[:200])

    try:
        tax_off = harness({'поля': {'tax_off': True}})
        residual = tax_off['R'] - tax_off['C'] - tax_off['aq'] - tax_off['fundY'] - tax_off['discY']
        check('расчёт: выключенные налоги не ломают баланс цели', abs(residual - tax_off['Ny']) < 1,
              f"Δ={residual-tax_off['Ny']:.6f}")
    except Exception as error:
        check('расчёт: сценарий без налогов выполняется', False, str(error)[:200])

    # 28.09, дорожная карта фаза 3.2: сценарий «сайт создан самостоятельно».
    # Выручка включает goalSelfSiteCost, поэтому кольцо отчёта обязано его показать.
    try:
        site_self = harness({'радио': {'site_mode': 'self'}})
        gap = site_self['R'] - sum(site_self['__parts'])
        check('сайт своими силами: сумма сегментов отчёта равна выручке', abs(gap) < 1,
              f"Δ={gap:.2f}; goalSelfSiteCost={site_self['goalSelfSiteCost']:.2f}")
    except Exception as error:
        check('сайт своими силами: сценарий расчёта выполняется', False, str(error)[:200])

    try:
        below_break_even = harness({'поля': {'current_rate': 1000}})
        zero_current_rate = harness({'поля': {'current_rate': 0}})
        check('З-001: запас выручки становится отрицательным ниже точки безубыточности',
              below_break_even['currentBreakEvenMargin'] < 0,
              f"запас={below_break_even['currentBreakEvenMargin']}")
        check('З-001: при нулевой текущей ставке запас выручки не подменяется ложным нулём',
              zero_current_rate['currentBreakEvenMargin'] is None,
              str(zero_current_rate['currentBreakEvenMargin']))
    except Exception as error:
        check('З-001: граничные сценарии запаса выручки выполняются', False, str(error)[:200])

    headless = command([NODE, str(TOOLS / 'проверить_report_headless.js'), str(ROOT)], cwd=TOOLS, timeout=300)
    check('report: headless 17 сценариев, 30 блоков, 13 таблиц',
          headless.returncode == 0 and '17 сценариев · 30 блоков · 13 таблиц · ошибок 0' in headless.stdout,
          (headless.stderr or headless.stdout).strip().split('\n')[-1][:200])
    finish()


def finish():
    for name, detail in ok:
        print('  ✓ ' + name + (f' — {detail}' if detail else ''))
    for name, detail in fail:
        print('  ✗ ' + name + (f' — {detail}' if detail else ''))
    print(f'\nитого активного контура: {len(ok)} прошло · {len(fail)} упало')
    if fail:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
