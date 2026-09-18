/* ═══ СЧЁТЧИК СЕРДЕЧЕК «СЧЁТИКС» — Cloudflare Worker ═══
   Хранит одно число в KV. Разворачивается за 10 минут, бесплатно.

   Подготовка:
     1. Workers & Pages → Create → Worker → имя schetix-hearts
     2. Storage → KV → Create namespace → имя HEARTS
     3. Worker → Settings → Variables → KV Namespace Bindings:
        переменная HEARTS → пространство HEARTS
     4. Settings → Variables → Environment Variables:
        СЕКРЕТ = придуманная строка (для метода /set)
     5. Вставить этот код → Deploy

   Адреса:
     GET /get                      → {"value":1780}
     GET /hit                      → +1 и новое значение
     GET /set?value=N&key=СЕКРЕТ   → задать значение вручную

   Один IP учитывается раз в сутки. */

const ДОМЕНЫ = [
  'https://schetix.ru',            // ← ваш домен
  'https://calc.schetix.ru',
  'https://вашпроект.tilda.ws',    // ← адрес на Tilda, пока нет своего домена
];

const КЛЮЧ = 'hearts';             // имя записи в KV
const СУТКИ = 60 * 60 * 24;        // срок жизни отметки об IP

function заголовки(origin) {
  const разрешён = ДОМЕНЫ.includes(origin) ? origin : ДОМЕНЫ[0];
  return {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': разрешён,
    'cache-control': 'no-store',
  };
}

async function хеш(строка) {
  const данные = new TextEncoder().encode(строка);
  const буфер = await crypto.subtle.digest('SHA-256', данные);
  return [...new Uint8Array(буфер)].slice(0, 8)
    .map(б => б.toString(16).padStart(2, '0')).join('');
}

export default {
  async fetch(запрос, окружение) {
    const url = new URL(запрос.url);
    const origin = запрос.headers.get('origin') || '';
    const шапка = заголовки(origin);

    if (запрос.method === 'OPTIONS') {
      return new Response(null, {
        headers: { ...шапка, 'access-control-allow-methods': 'GET,OPTIONS' },
      });
    }

    const текущее = async () => parseInt(await окружение.HEARTS.get(КЛЮЧ) || '0', 10);

    /* ── прочитать ── */
    if (url.pathname === '/get') {
      return new Response(JSON.stringify({ value: await текущее() }), { headers: шапка });
    }

    /* ── увеличить ── */
    if (url.pathname === '/hit') {
      const ip = запрос.headers.get('cf-connecting-ip') || '0';
      const отметка = 'ip:' + await хеш(ip);
      const уже = await окружение.HEARTS.get(отметка);
      let значение = await текущее();

      if (!уже) {
        значение += 1;
        await окружение.HEARTS.put(КЛЮЧ, String(значение));
        await окружение.HEARTS.put(отметка, '1', { expirationTtl: СУТКИ });
      }
      return new Response(JSON.stringify({ value: значение, засчитано: !уже }), { headers: шапка });
    }

    /* ── задать значение вручную (точка отсчёта) ── */
    if (url.pathname === '/set') {
      if (url.searchParams.get('key') !== окружение.СЕКРЕТ) {
        return new Response(JSON.stringify({ error: 'нет доступа' }), { status: 403, headers: шапка });
      }
      const значение = parseInt(url.searchParams.get('value') || '0', 10);
      await окружение.HEARTS.put(КЛЮЧ, String(значение));
      return new Response(JSON.stringify({ value: значение }), { headers: шапка });
    }

    return new Response(JSON.stringify({ error: 'неизвестный адрес' }), { status: 404, headers: шапка });
  },
};
