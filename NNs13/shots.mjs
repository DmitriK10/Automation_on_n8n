// Скриншоты урока 13. Каждый шаг — отдельный вызов: node shots.mjs <шаг>
import { attach, signIn, BASE } from './cdp.mjs';

const EMAIL = process.env.N8N_EMAIL;
const PASS = process.env.N8N_PASS;
const step = process.argv[2] || 'all';

const page = await attach(9222);
await page.setViewport(1680, 1050);

const login = await signIn(page, EMAIL, PASS);
if (!login.signedIn) { console.error('вход не удался'); await page.detach(); process.exit(1); }

async function mouseClick(x, y, clickCount = 1) {
  await page.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await page.sleep(120);
  for (let i = 1; i <= clickCount; i++) {
    await page.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: i });
    await page.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: i });
    await page.sleep(90);
  }
}

async function rectOf(nodeId) {
  const r = await page.evaluate(`(() => {
    const el = document.querySelector('[data-id="${nodeId}"]');
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return { x: b.x + b.width / 2, y: b.y + b.height / 2, w: b.width, h: b.height };
  })()`);
  return r;
}

async function openWorkflow(id, waitMs = 8000) {
  await page.goto(`${BASE}/workflow/${id}`, waitMs);
  await page.waitFor('document.querySelector(".vue-flow__node")', 30000);
  await page.sleep(1200);
}

async function closePanels() {
  await page.evaluate(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => /close|закрыть/i.test(x.getAttribute('aria-label') || ''));
    if (b) b.click();
    return true;
  })()`);
  await page.sleep(400);
}

const run = {
  async canvas() {
    await openWorkflow('Hw13CenterAuto01');
    await page.screenshot('01-center-canvas');
    console.log('01-center-canvas снят');
  },

  async schedule() {
    await openWorkflow('Hw13CenterAuto01');
    const r = await rectOf('main-cron');
    console.log('нода расписания:', JSON.stringify(r));
    if (!r) throw new Error('нода расписания не найдена');
    await mouseClick(r.x, r.y, 2);
    await page.sleep(2500);
    const shown = await page.evaluate('document.body.innerText.includes("Trigger at Hour") || document.body.innerText.includes("Days")');
    console.log('панель параметров открылась:', shown);
    await page.screenshot('05-schedule-trigger');
    console.log('05-schedule-trigger снят');
  },

  async subsearch() {
    await openWorkflow('Hw13SearchKb0001');
    await page.screenshot('02-subworkflow-published');
    console.log('02-subworkflow-published снят');
  },

  async errors() {
    await openWorkflow('Hw13ErrorHook001');
    await page.screenshot('03-error-workflow');
    console.log('03-error-workflow снят');
  },

  async settings() {
    await openWorkflow('Hw13CenterAuto01');
    // меню "Actions" в шапке -> пункт Settings
    const clicked = await page.evaluate(`(() => {
      const b = document.querySelector('button[aria-label="Actions"]');
      if (!b) return 'кнопка Actions не найдена';
      b.click();
      return 'Actions нажата';
    })()`);
    console.log(clicked);
    await page.sleep(1200);
    const items = await page.evaluate(`(() => [...document.querySelectorAll('[role=menuitem], .n8n-menu-item, li')]
      .map(e => (e.textContent || '').trim()).filter(t => t && t.length < 40).slice(0, 25))()`);
    console.log('пункты меню:', JSON.stringify(items));
    const opened = await page.evaluate(`(() => {
      const cands = [...document.querySelectorAll('[role=menuitem], .n8n-menu-item, li, button, a, div')];
      const el = cands.find(e => /^\\s*Settings\\s*$/i.test((e.textContent || '').trim()) && e.getBoundingClientRect().width > 0);
      if (!el) return 'пункт Settings не найден';
      el.click();
      return 'Settings нажат';
    })()`);
    console.log(opened);
    await page.sleep(2500);
    const txt = await page.evaluate('document.body.innerText');
    console.log('видно Error Workflow:', /Error Workflow/i.test(txt));
    await page.screenshot('04-settings-error-workflow');
    console.log('04-settings-error-workflow снят');
    return txt.slice(0, 500);
  },
async chat() {
    await openWorkflow('Hw13CenterAuto01');

    // В редакторе чат работает через тестовый вебхук: сначала включаем прослушивание.
    const started = await page.evaluate(`(() => {
      const b = document.querySelector('button[data-test-id="execute-workflow-button"]');
      if (!b) return 'кнопка запуска не найдена';
      b.click();
      return 'запуск тестового прослушивания';
    })()`);
    console.log(started);
    await page.sleep(4000);

    const opened = await page.evaluate(`(() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => /Type message/i.test(t.getAttribute('placeholder') || ''));
      if (ta) return 'чат уже открыт';
      const b = document.querySelector('button[data-test-id="workflow-chat-button"]');
      if (b) { b.click(); return 'чат открыт кнопкой'; }
      return 'кнопка чата не найдена';
    })()`);
    console.log(opened);
    await page.sleep(3000);

    const focused = await page.evaluate(`(() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => /Type message/i.test(t.getAttribute('placeholder') || ''));
      if (!ta) return 'поле чата не найдено';
      ta.focus();
      ta.click();
      return 'поле чата в фокусе: ' + (document.activeElement === ta);
    })()`);
    console.log(focused);
    await page.sleep(500);

    const q = 'Сколько дней даётся на возврат товара надлежащего качества?';
    await page.send('Input.insertText', { text: q });
    await page.sleep(700);
    const typedNow = await page.evaluate(`(() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => /Type message/i.test(t.getAttribute('placeholder') || ''));
      return ta ? ta.value : 'нет поля';
    })()`);
    console.log('в поле ввода:', JSON.stringify(typedNow));

    // кнопка отправки живёт в блоке .chat-inputs
    const sent = await page.evaluate(`(() => {
      const b = document.querySelector('.chat-inputs button');
      if (!b) return 'кнопка отправки не найдена';
      b.click();
      return 'кнопка отправки нажата';
    })()`);
    console.log(sent);
    await page.sleep(1500);

    const got = await page.waitFor(
      `document.body.innerText.includes('14 дней') || document.body.innerText.includes('четырнадцат')`,
      60000,
      700,
    );
    console.log('ответ получен:', got);
    const txt = await page.evaluate('document.body.innerText');
    const at = txt.indexOf('Сколько дней');
    console.log('фрагмент:', JSON.stringify(txt.slice(at, at + 400)));
    await page.screenshot('06-chat-answer');
    console.log('06-chat-answer снят');
  },

  async executions() {
    await page.goto(`${BASE}/executions`, 8000);
    await page.sleep(3000);
    await page.screenshot('07-executions-list');
    console.log('07-executions-list снят');
  },

  async exec() {
    const id = process.env.EXEC_ID || '143';
    const wf = process.env.EXEC_WF || 'Hw13CenterAuto01';
    await page.goto(`${BASE}/workflow/${wf}/executions/${id}`, 9000);
    await page.sleep(3000);
    await page.screenshot(`06-execution-${id}`);
    console.log(`06-execution-${id} снят`);

    // открываем последнюю ноду, чтобы было видно готовый ответ
    const clicked = await page.evaluate(`(() => {
      const el = document.querySelector('[data-id="main-final"]') || document.querySelector('[data-id="main-answer"]');
      if (!el) return 'нода не найдена';
      const b = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2) });
    })()`);
    console.log('координаты ноды:', clicked);
    try {
      const p = JSON.parse(clicked);
      await mouseClick(p.x, p.y, 1);
      await page.sleep(2500);
      const txt = await page.evaluate('document.body.innerText');
      console.log('в панели есть ответ:', /14 дней/.test(txt));
      await page.screenshot(`06b-execution-${id}-output`);
      console.log(`06b-execution-${id}-output снят`);
    } catch { console.log('клик по ноде не удался'); }
  },

  async mailpit() {
    const base = process.env.MAILPIT_BASE || 'http://localhost:18025';
    // берём самое свежее письмо о сбое через API mailpit
    const list = await (await fetch(`${base}/api/v1/messages?limit=60`)).json();
    const err = (list.messages || []).filter(m => /^Сбой автоматизации/.test(m.Subject || ''));
    if (!err.length) throw new Error('писем о сбое нет');
    const msg = err[0];
    console.log('письмо:', msg.ID, msg.Subject, msg.Created);

    await page.goto(`${base}/view/${msg.ID}`, 7000);
    await page.sleep(3000);
    const txt = await page.evaluate('document.body.innerText');
    console.log('в письме есть ID выполнения:', /ID выполнения/.test(txt), '| про Qdrant:', /Qdrant/.test(txt));
    await page.screenshot('08-error-email');
    console.log('08-error-email снят');
  },
};

if (step === 'all') {
  for (const k of Object.keys(run)) { await run[k](); }
} else {
  if (!run[step]) { console.error('неизвестный шаг:', step); process.exit(1); }
  await run[step]();
}

await page.detach();