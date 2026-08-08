#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает web/report.html из каркаса и блоков в папке «части».

    python3 собрать.py            собрать и проверить
    python3 собрать.py --проверка только проверить текущий report.html

Каркас — это report.html, в котором вынесенные блоки заменены на метку
<!--БЛОК:имя-->. Файл части/имя.html подставляется на место метки.

Если хоть одна проверка не прошла — report.html НЕ перезаписывается.
"""
import io, os, re, sys, subprocess, shutil, datetime

ЗДЕСЬ  = os.path.dirname(os.path.abspath(__file__))
ЧАСТИ  = os.path.join(ЗДЕСЬ, 'части')
КАРКАС = os.path.join(ЧАСТИ, 'каркас.html')
ИТОГ   = os.path.join(ЗДЕСЬ, 'report.html')
АРХИВ  = os.path.abspath(os.path.join(ЗДЕСЬ, '..', '_архив', 'вёрстка'))
СТОРОЖ = os.path.abspath(os.path.join(ЗДЕСЬ, '..', '_архив', 'скрипты', 'проверка_логотипа.py'))

VOID = {'br','img','input','meta','link','hr','source','area','col','embed','track','wbr',
        'circle','path','rect','polygon','line','ellipse','stop','use','polyline'}


def читать(п):
    return io.open(п, encoding='utf-8').read()


# ---------------------------------------------------------------- сборка
def собрать():
    if not os.path.exists(КАРКАС):
        raise SystemExit('нет файла ' + КАРКАС)
    s = читать(КАРКАС)
    метки = re.findall(r'<!--БЛОК:([\w-]+)-->', s)
    for имя in метки:
        путь = os.path.join(ЧАСТИ, имя + '.html')
        if not os.path.exists(путь):
            raise SystemExit('нет блока ' + путь)
        s = s.replace('<!--БЛОК:%s-->\n' % имя, читать(путь).rstrip('\n') + '\n')
        s = s.replace('<!--БЛОК:%s-->' % имя, читать(путь).rstrip('\n'))
    return s, метки


# ------------------------------------------------------------- проверки
def без_кода(s):
    """Заменяет содержимое <script> и <style> пробелами, сохраняя длину.
    Внутри JS в строках встречается разметка — она не должна считаться тегами."""
    def глушь(m):
        нач, тело, кон = m.group(1), m.group(2), m.group(3)
        return нач + re.sub(r'[^\n]', ' ', тело) + кон
    s = re.sub(r'(<script[^>]*>)([\s\S]*?)(</script>)', глушь, s)
    s = re.sub(r'(<style[^>]*>)([\s\S]*?)(</style>)', глушь, s)
    s = re.sub(r'<!--[\s\S]*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s)
    return s


def теги(s):
    s = без_кода(s)
    стек, ошибки = [], []
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>', s):
        зак, имя, атр, само = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if имя in VOID or само == '/':
            continue
        if зак:
            if стек and стек[-1][0] == имя:
                стек.pop()
            else:
                ошибки.append('лишний </%s> поз.%d' % (имя, m.start()))
        else:
            стек.append((имя, m.start()))
    ошибки += ['не закрыт <%s> поз.%d' % (и, п) for и, п in стек]
    return ошибки


def детей_в_wp(s):
    s = без_кода(s)
    старт = s.index('<div class="wp">') + len('<div class="wp">')
    глуб, дети, тек = 0, 0, None
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>', s[старт:]):
        зак, имя, само = m.group(1), m.group(2).lower(), m.group(4)
        if зак:
            глуб -= 1
            if глуб == 0 and тек is not None:
                дети += 1
                тек = None
            if глуб < 0:
                break
        else:
            if имя in VOID or само == '/':
                continue
            if глуб == 0:
                тек = m.start()
            глуб += 1
    return дети


def проверить(s, ожидать_блоков=18):
    беды = []

    т = теги(s)
    if т:
        беды += ['ТЕГИ: ' + х for х in т[:5]]

    css = s[s.index('<style>'):s.index('</style>')]
    раз = css.count('{') - css.count('}')
    if раз:
        беды.append('CSS: дисбаланс скобок %+d' % раз)

    использованы = set(re.findall(r'var\((--[\w-]+)\)', s))
    объявлены = set(re.findall(r'(--[\w-]+)\s*:', s))
    нет = использованы - объявлены
    if нет:
        беды.append('ПАЛИТРА: не объявлены ' + ', '.join(sorted(нет)))

    # Циклическое объявление вида «--x: var(--x)» делает переменную
    # недействительной — цвет молча пропадает. Обычные проверки это не ловят.
    циклы = re.findall(r'(--[\w-]+)\s*:\s*var\(\1\)', s)
    if циклы:
        беды.append('ПАЛИТРА: ссылка на себя — ' + ', '.join(sorted(set(циклы))))

    д = детей_в_wp(s)
    if д != ожидать_блоков:
        беды.append('СТРУКТУРА: блоков в .wp — %d, ждали %d' % (д, ожидать_блоков))

    врем = os.path.join(ЗДЕСЬ, '.проверка.html')
    io.open(врем, 'w', encoding='utf-8').write(s)
    try:
        код = ("const h=require('fs').readFileSync(process.argv[1],'utf8');"
               "const m=h.match(/<script>([\\s\\S]*)<\\/script>/);"
               "if(!m){console.error('нет script');process.exit(1)}"
               "new Function(m[1]);")
        r = subprocess.run(['node', '-e', код, врем], capture_output=True, text=True)
        if r.returncode:
            беды.append('JS: ' + (r.stderr.strip().split('\n')[0] if r.stderr else 'ошибка'))
    except FileNotFoundError:
        беды.append('JS: node не найден — проверка пропущена')
    finally:
        if os.path.exists(врем):
            os.remove(врем)

    return беды


def сторож():
    if not os.path.exists(СТОРОЖ):
        return 'сторож логотипа не найден'
    r = subprocess.run(['python3', СТОРОЖ], capture_output=True, text=True)
    вых = (r.stdout or '') + (r.stderr or '')
    return None if 'ЛОГОТИП В ПОРЯДКЕ' in вых else 'ЛОГОТИП: ' + вых.strip()[:200]


# ------------------------------------------------------------------ ход
def главное():
    только_проверка = '--проверка' in sys.argv

    if только_проверка:
        s = читать(ИТОГ)
        print('проверяю текущий report.html')
    else:
        s, метки = собрать()
        print('каркас + блоки: ' + ', '.join(метки))

    беды = проверить(s)

    if беды:
        print('\n  СБОРКА ОСТАНОВЛЕНА\n')
        for б in беды:
            print('  ✗ ' + б)
        print('\nreport.html не тронут.')
        return 1

    if только_проверка:
        л = сторож()
        if л:
            print('  ✗ ' + л)
            return 1
        print('  ✓ теги · CSS · палитра · %d блоков · JS · логотип' % детей_в_wp(s))
        return 0

    # архивная копия прежней версии
    if os.path.exists(ИТОГ):
        os.makedirs(АРХИВ, exist_ok=True)
        было = [int(re.findall(r'report_prev(\d+)\.html', f)[0])
                for f in os.listdir(АРХИВ) if re.match(r'report_prev\d+\.html$', f)]
        n = (max(было) + 1) if было else 1
        shutil.copy2(ИТОГ, os.path.join(АРХИВ, 'report_prev%d.html' % n))
        print('прежняя версия → _архив/вёрстка/report_prev%d.html' % n)

    io.open(ИТОГ, 'w', encoding='utf-8').write(s)

    л = сторож()
    if л:
        print('  ✗ ' + л)
        return 1

    print('  ✓ теги · CSS · палитра · %d блоков · JS · логотип' % детей_в_wp(s))
    print('report.html собран, %d КБ' % (len(s.encode()) // 1024))

    # Сверка с прежней версией: показывает, что правка задела в оформлении,
    # включая соседние элементы, которых менять не просили.
    прежний = os.path.join(АРХИВ, 'report_prev%d.html' % n) if 'n' in dir() else None
    ВЁРСТКА = os.path.abspath(os.path.join(
        ЗДЕСЬ, '..', '_архив', 'скрипты', 'проверка_вёрстки.py'))
    if os.path.exists(ВЁРСТКА):
        кмд = ['python3', ВЁРСТКА, ИТОГ]
        if прежний and os.path.exists(прежний):
            кмд += ['--было', прежний]
        r = subprocess.run(кмд, capture_output=True, text=True)
        вых = (r.stdout or '').strip()
        if вых:
            print()
            print(вых)
    return 0


if __name__ == '__main__':
    sys.exit(главное())
