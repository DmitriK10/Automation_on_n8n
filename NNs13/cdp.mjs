// Скриншоты урока 12 через CDP. Привязываемся к уже открытой вкладке,
// чтобы снимать то же окно, которое видит пользователь.
import { writeFileSync, mkdirSync } from 'node:fs';

const PORT = 9222;
const OUT = 'n8n-lab/hw13/shots';
const BASE = process.env.N8N_BASE || 'http://localhost:15678';

export async function attach(port = PORT, urlMatch = '') {
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const pages = list.filter((t) => t.type === 'page');
  const target = pages.find((t) => urlMatch && t.url.includes(urlMatch)) || pages[0];
  if (!target) throw new Error('нет открытых вкладок');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = (e) => rej(new Error('ws connect failed'));
  });

  let seq = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(m.error.message));
      else resolve(m.result);
    }
  };
  const send = (method, params = {}) => {
    const id = ++seq;
    ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  };

  await send('Page.enable');
  await send('Runtime.enable');

  const page = {
    targetUrl: target.url,
    send,
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
    async goto(url, waitMs = 2000) {
      await send('Page.navigate', { url });
      await page.waitFor('document.readyState === "complete"', 30000).catch(() => {});
      await page.sleep(waitMs);
    },
    async evaluate(expression) {
      const r = await send('Runtime.evaluate', {
        expression, awaitPromise: true, returnByValue: true, userGesture: true,
      });
      if (r.exceptionDetails) throw new Error('evaluate: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result?.value;
    },
    async waitFor(expr, timeout = 25000, interval = 300) {
      const t0 = Date.now();
      for (;;) {
        let ok = false;
        try { ok = await page.evaluate(`!!(${expr})`); } catch { ok = false; }
        if (ok) return true;
        if (Date.now() - t0 > timeout) return false;
        await page.sleep(interval);
      }
    },
    async setViewport(width, height) {
      await send('Emulation.setDeviceMetricsOverride', {
        width, height, deviceScaleFactor: 1, mobile: false,
      });
      await page.sleep(600);
    },
    async screenshot(name) {
      mkdirSync(OUT, { recursive: true });
      const { data } = await send('Page.captureScreenshot', { format: 'png', fromSurface: true });
      const file = `${OUT}/${name}.png`;
      writeFileSync(file, Buffer.from(data, 'base64'));
      return file;
    },
    async detach() { try { ws.close(); } catch {} },
  };
  return page;
}

export { BASE };
export async function signIn(page, email, password) {
  // Если сессия уже есть, /home/workflows не перебросит на вход — не тратим попытки.
  await page.goto(BASE + '/home/workflows', 4000);
  const already = await page.evaluate('location.href');
  if (!already.includes('/signin')) return { signedIn: true, url: already, reused: true };

  await page.goto(BASE + '/signin', 3000);
  const ok = await page.waitFor('document.querySelector("input[type=email], input[name=email]")', 20000);
  if (!ok) return { signedIn: false, reason: 'форма входа не найдена' };

  await page.evaluate(`(() => {
    const email = ${JSON.stringify(email)};
    const pass = ${JSON.stringify(password)};
    const inputs = [...document.querySelectorAll('input')];
    const e = inputs.find(i => i.type === 'email' || i.name === 'email');
    const p = inputs.find(i => i.type === 'password');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(e, email); e.dispatchEvent(new Event('input', { bubbles: true }));
    setter.call(p, pass); p.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await page.sleep(500);
  await page.evaluate(`(() => {
    const btn = [...document.querySelectorAll('button')].find(b => /sign in|войти/i.test(b.textContent));
    if (btn) btn.click();
    return !!btn;
  })()`);
  await page.sleep(4000);
  const url = await page.evaluate('location.href');
  return { signedIn: !url.includes('/signin'), url };
}


