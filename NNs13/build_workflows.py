# -*- coding: utf-8 -*-
"""Сборка центра автоматизации для урока 13.

Четыре сценария:
  1. Центр автоматизации      — две точки входа, вызовы Subworkflow
  2. Subworkflow «Поиск в базе»
  3. Subworkflow «Отправка результата на почту»
  4. Error Workflow

Параметры HTTP-нод взяты из рабочего сценария урока 12, чтобы конфигурация
была проверенной, а не выдуманной.
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows")

MAIN_ID = "Hw13CenterAuto01"
SEARCH_ID = "Hw13SearchKb0001"
MAIL_ID = "Hw13SendMail001"
ERROR_ID = "Hw13ErrorHook001"

CRED_GIGA = {"httpHeaderAuth": {"id": "ppkK1prgCpngzY4c",
                                "name": "GigaChat — ключ авторизации (RAG)"}}
CRED_EMB = {"httpHeaderAuth": {"id": "AcEr1hBxvjAjSNgo",
                               "name": "Эмбеддинги ProxyAPI (RAG)"}}
CRED_SMTP = {"smtp": {"id": "Hw08SmtpMail0001",
                      "name": "SMTP — отправка писем (n8n-lab)"}}

FROM_ADDR = "manager@n8n-lab.local"
TO_ADDR = "owner@n8n-lab.local"

# Вопрос, который подставляется при запуске по расписанию
SCHEDULED_QUESTION = "Какие условия возврата товара надлежащего качества?"


def sticky(content, x, y, w=420, h=260, color=5):
    return {
        "parameters": {"content": content, "height": h, "width": w, "color": color},
        "id": "note-" + str(abs(hash(content)) % 10**8),
        "name": "Заметка — " + content.split("\n")[0][:40],
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [x, y],
    }


def code(name, js, x, y, nid):
    return {
        "parameters": {"jsCode": js},
        "id": nid, "name": name,
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [x, y],
    }


def http(name, params, x, y, nid, creds=None):
    node = {"parameters": params, "id": nid, "name": name,
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [x, y]}
    if creds:
        node["credentials"] = creds
    return node


def call_sub(name, target_id, x, y, nid):
    return {
        "parameters": {
            "workflowId": {"__rl": True, "value": target_id, "mode": "id"},
            "mode": "once",
            "options": {"waitForSubWorkflow": True},
        },
        "id": nid, "name": name,
        "type": "n8n-nodes-base.executeWorkflow", "typeVersion": 1.3,
        "position": [x, y],
    }


def link(src, dst):
    return {src: {"main": [[{"node": dst, "type": "main", "index": 0}]]}}


def merge_conns(*parts):
    out = {}
    for p in parts:
        out.update(p)
    return out


# ---------------------------------------------------------------- 2. поиск
SEARCH_CODE_PREP = """// На вход приходит объект { query } из основного сценария.
// Если вопроса нет, подставляем дежурный — так Subworkflow можно
// вызывать и без подготовки.
const q = ($json.query || '').toString().trim();
return [{ json: { query: q || 'условия возврата товара' } }];"""

SEARCH_VECTOR = """// Вектор вопроса -> тело запроса для Qdrant.
const vec = $json.data[0].embedding;
return [{ json: { vector: vec, dim: vec.length } }];"""

SEARCH_CONTEXT = """// Ответ Qdrant превращаем в чистый текст для модели.
// Вопрос прокидываем дальше: его ждёт основной сценарий.
const query = $('Подготовка запроса').first().json.query;
const res = $json.result || {};
const hits = Array.isArray(res) ? res : (res.points || []);
if (!hits.length) {
  return [{ json: { query, found: false, hits: 0, top_score: 0, context: '' } }];
}
const parts = hits.map((h, i) =>
  '[' + (i + 1) + '] (близость ' + (h.score ?? 0).toFixed(3) + ')\\n' + ((h.payload || {}).text || '')
);
return [{
  json: {
    query,
    found: true,
    hits: hits.length,
    top_score: hits[0].score ?? 0,
    context: parts.join('\\n\\n---\\n\\n'),
  },
}];"""

search = {
    "name": "Урок 13 — Subworkflow «Поиск в базе»",
    "nodes": [
        sticky("Subworkflow «Поиск в базе»\n\nПереиспользуемый блок: вопрос -> вектор -> "
               "поиск в Qdrant -> готовый контекст.\nВызывается из основного сценария, "
               "сам по себе не запускается.\nВход: query\nВыход: query, context, hits, top_score",
               40, 60, 520, 240),
        {
            "parameters": {"inputSource": "passthrough"},
            "id": "sw-search-start", "name": "Старт поиска",
            "type": "n8n-nodes-base.executeWorkflowTrigger", "typeVersion": 1.2,
            "position": [60, 380],
        },
        code("Подготовка запроса", SEARCH_CODE_PREP, 300, 380, "sw-search-prep"),
        http("Эмбеддинги вопроса", {
            "method": "POST",
            "url": "https://api.proxyapi.ru/openai/v1/embeddings",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={\n  \"model\": \"text-embedding-3-small\",\n"
                        "  \"input\": [{{ JSON.stringify($json.query) }}]\n}",
            "options": {"timeout": 60000, "response": {"response": {"neverError": False}}},
        }, 540, 380, "sw-search-emb", CRED_EMB),
        code("Сборка запроса", SEARCH_VECTOR, 780, 380, "sw-search-vec"),
        http("Поиск в Qdrant", {
            "method": "POST",
            "url": "http://qdrant-lab:6333/collections/n8n-lab-kb/points/search",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={\n  \"vector\": {{ JSON.stringify($json.vector) }},\n"
                        "  \"limit\": 4,\n  \"with_payload\": true\n}",
            "options": {"timeout": 60000, "response": {"response": {"neverError": False}}},
        }, 1020, 380, "sw-search-qdrant"),
        code("Подготовка контекста", SEARCH_CONTEXT, 1260, 380, "sw-search-ctx"),
    ],
    "connections": merge_conns(
        link("Старт поиска", "Подготовка запроса"),
        link("Подготовка запроса", "Эмбеддинги вопроса"),
        link("Эмбеддинги вопроса", "Сборка запроса"),
        link("Сборка запроса", "Поиск в Qdrant"),
        link("Поиск в Qdrant", "Подготовка контекста"),
    ),
    "settings": {"executionOrder": "v1", "timezone": "Europe/Moscow",
                 "errorWorkflow": ERROR_ID},
}

# ---------------------------------------------------------------- 3. почта
MAIL_CODE = """// Subworkflow отправки: принимает to, subject, text.
// mail_body — готовый текст письма; text — короткий ответ для чата.
const to = ($json.to || 'owner@n8n-lab.local').toString();
const subject = ($json.subject || 'Письмо из центра автоматизации').toString();
const text = ($json.mail_body || $json.text || '').toString();
return [{ json: { to, subject, text } }];"""

MAIL_RESULT = """// Возвращаем основному сценарию короткий отчёт об отправке.
return [{
  json: {
    sent: true,
    to: $('Подготовка письма').first().json.to,
    subject: $('Подготовка письма').first().json.subject,
  },
}];"""

mail = {
    "name": "Урок 13 — Subworkflow «Отправка результата на почту»",
    "nodes": [
        sticky("Subworkflow «Отправка результата на почту»\n\nПереиспользуемый блок: "
               "любой сценарий передаёт to, subject, text — и получает готовое письмо.\n"
               "Вход: to, subject, text\nВыход: sent, to, subject",
               40, 60, 520, 220),
        {
            "parameters": {"inputSource": "passthrough"},
            "id": "sw-mail-start", "name": "Старт отправки",
            "type": "n8n-nodes-base.executeWorkflowTrigger", "typeVersion": 1.2,
            "position": [60, 360],
        },
        code("Подготовка письма", MAIL_CODE, 300, 360, "sw-mail-prep"),
        {
            "parameters": {
                "fromEmail": FROM_ADDR,
                "toEmail": "={{ $json.to }}",
                "subject": "={{ $json.subject }}",
                "emailFormat": "text",
                "text": "={{ $json.text }}",
                "options": {},
            },
            "id": "sw-mail-send", "name": "Письмо",
            "type": "n8n-nodes-base.emailSend", "typeVersion": 2.1,
            "position": [540, 360],
            "credentials": CRED_SMTP,
        },
        code("Итог отправки", MAIL_RESULT, 780, 360, "sw-mail-out"),
    ],
    "connections": merge_conns(
        link("Старт отправки", "Подготовка письма"),
        link("Подготовка письма", "Письмо"),
        link("Письмо", "Итог отправки"),
    ),
    "settings": {"executionOrder": "v1", "timezone": "Europe/Moscow",
                 "errorWorkflow": ERROR_ID},
}

# ---------------------------------------------------------------- 1. центр
ENTRY_CODE = """// Две точки входа сводим в одну ноду — это и есть развилка из урока.
// Пришло из чата — берём вопрос пользователя.
// Запуск по расписанию — подставляем дежурный вопрос из расписания.
const fromChat = ($json.chatInput || '').toString().trim();
const scheduled = %s;
const query = fromChat || scheduled;
return [{
  json: {
    query,
    source: fromChat ? 'чат' : 'расписание',
    got_at: new Date().toISOString(),
  },
}];""" % json.dumps(SCHEDULED_QUESTION, ensure_ascii=False)

RQUID_CODE = """// GigaChat требует уникальный RqUID на каждый запрос токена.
const u = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
  const r = Math.floor(Math.random() * 16);
  return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
});
return [{ json: { rquid: u } }];"""

ANSWER_CODE = """// Достаём текст ответа и собираем письмо для Subworkflow отправки.
const txt = ($json.choices && $json.choices[0] && $json.choices[0].message
  && $json.choices[0].message.content) || 'Не удалось получить ответ.';
const found = $('Поиск в базе').first().json;
const query = found.query;
const text = txt.trim();

const body = [
  'Вопрос: ' + query,
  'Ответ: ' + text,
  '',
  'Найдено фрагментов: ' + found.hits + ' (близость ' + Number(found.top_score).toFixed(3) + ')',
  'Источник: запуск ' + $('Единая точка входа').first().json.source,
  'Время: ' + new Date().toLocaleString('ru-RU'),
].join('\\n');

return [{
  json: {
    text,
    query,
    to: %s,
    subject: 'Центр автоматизации: ответ по базе знаний',
    mail_body: body,
  },
}];""" % json.dumps(TO_ADDR, ensure_ascii=False)

FINAL_CODE = """// Ответ в окно чата. Берём текст у предыдущего шага, а не у почтового
// Subworkflow, иначе чат показал бы служебный отчёт об отправке.
const a = $('Разбор ответа').first().json;
return [{ json: { output: a.text, text: a.text } }];"""

main = {
    "name": "Урок 13 — Центр автоматизации",
    "nodes": [
        sticky("Центр автоматизации\n\nДве точки входа: чат и расписание.\n"
               "Развилка сводит их в один вопрос.\nПоиск и отправка письма вынесены "
               "в Subworkflow — их можно вызывать из других сценариев.",
               40, 40, 480, 220),
        {
            "parameters": {
                "public": True,
                "initialMessages": "Здравствуйте! Это центр автоматизации. "
                                   "Спросите что-нибудь про доставку, возврат или гарантию.",
                "options": {},
            },
            "id": "main-chat", "name": "Чат",
            "type": "@n8n/n8n-nodes-langchain.chatTrigger", "typeVersion": 1.4,
            "position": [60, 340],
            "webhookId": "center-hw13-chat",
        },
        {
            "parameters": {
                "rule": {"interval": [{
                    "field": "days",
                    "daysInterval": 1,
                    "triggerAtHour": 9,
                    "triggerAtMinute": 0,
                }]},
            },
            "id": "main-cron", "name": "Расписание",
            "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.3,
            "position": [60, 560],
        },
        code("Единая точка входа", ENTRY_CODE, 320, 440, "main-entry"),
        call_sub("Поиск в базе", SEARCH_ID, 560, 440, "main-call-search"),
        code("Подготовка токена", RQUID_CODE, 800, 440, "main-rquid"),
        http("Токен GigaChat", {
            "method": "POST",
            "url": "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Accept", "value": "application/json"},
                {"name": "RqUID", "value": "={{ $json.rquid }}"}]},
            "sendBody": True,
            "contentType": "form-urlencoded",
            "bodyParameters": {"parameters": [
                {"name": "scope", "value": "GIGACHAT_API_PERS"}]},
            "options": {"timeout": 60000, "allowUnauthorizedCerts": True,
                        "response": {"response": {"neverError": False}}},
        }, 1040, 440, "main-token", CRED_GIGA),
        http("Ответ GigaChat", {
            "method": "POST",
            "url": "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization",
                 "value": "=Bearer {{ $('Токен GigaChat').first().json.access_token }}"},
                {"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                '={\n'
                '  "model": "GigaChat",\n'
                '  "temperature": 0.2,\n'
                '  "messages": [\n'
                '    { "role": "system", "content": "Ты — помощник интернет-магазина КофеТочка. '
                'Отвечай ТОЛЬКО по фрагментам базы знаний, которые даны ниже. Если ответа в них '
                'нет — так и скажи: \\"В базе знаний нет информации по данному запросу\\". '
                'Не придумывай факты. Отвечай коротко: 1-3 предложения, по-русски." },\n'
                '    { "role": "user", "content": {{ JSON.stringify("Вопрос клиента: " + '
                "$('Поиск в базе').first().json.query + \"\\n\\nФрагменты базы знаний:\\n\" + "
                "$('Поиск в базе').first().json.context) }} }\n"
                '  ]\n'
                '}'
            ),
            "options": {"timeout": 90000, "allowUnauthorizedCerts": True,
                        "response": {"response": {"neverError": False}}},
        }, 1280, 440, "main-answer"),
        code("Разбор ответа", ANSWER_CODE, 1520, 440, "main-parse"),
        call_sub("Отправка на почту", MAIL_ID, 1760, 440, "main-call-mail"),
        code("Ответ в чат", FINAL_CODE, 2000, 440, "main-final"),
    ],
    "connections": merge_conns(
        link("Чат", "Единая точка входа"),
        link("Расписание", "Единая точка входа"),
        link("Единая точка входа", "Поиск в базе"),
        link("Поиск в базе", "Подготовка токена"),
        link("Подготовка токена", "Токен GigaChat"),
        link("Токен GigaChat", "Ответ GigaChat"),
        link("Ответ GigaChat", "Разбор ответа"),
        link("Разбор ответа", "Отправка на почту"),
        link("Отправка на почту", "Ответ в чат"),
    ),
    "settings": {"executionOrder": "v1", "timezone": "Europe/Moscow",
                 "errorWorkflow": ERROR_ID},
}

# ---------------------------------------------------------------- 4. ошибки
ERROR_CODE = """// Error Trigger отдаёт данные о сбое. Разбираем их аккуратно:
// какие именно поля заполнены, зависит от версии n8n.
const wf = $json.workflow || {};
const ex = $json.execution || {};
const err = ex.error || $json.error || {};
const trigger = $json.trigger || {};

function nodeNameOf() {
  if (err.node && typeof err.node === 'object') return err.node.name || err.node.type || 'неизвестна';
  if (typeof err.node === 'string' && err.node) return err.node;
  if (ex.lastNodeExecuted) return ex.lastNodeExecuted;
  if (trigger && (trigger.name || trigger.type)) return trigger.name || trigger.type;
  return 'неизвестна';
}

const workflowName = wf.name || ('id ' + (wf.id || 'неизвестен'));
const nodeName = nodeNameOf();
const message = err.message || err.description || 'описание не передано';
const execId = ex.id || 'неизвестен';
const mode = ex.mode || 'неизвестен';

const text = [
  'Сценарий: ' + workflowName,
  'Нода со сбоем: ' + nodeName,
  'Ошибка: ' + message,
  'Режим запуска: ' + mode,
  'ID выполнения: ' + execId,
  'Время: ' + new Date().toLocaleString('ru-RU'),
  '',
  'Откройте Executions в n8n и найдите выполнение ' + execId + '.',
].join('\\n');

return [{
  json: {
    subject: 'Сбой автоматизации: ' + workflowName,
    text,
    workflow: workflowName,
    node: nodeName,
    execution: execId,
  },
}];"""

error_wf = {
    "name": "Урок 13 — Error Workflow (уведомление о сбоях)",
    "nodes": [
        sticky("Error Workflow\n\nПривязан к основному сценарию и к обоим Subworkflow.\n"
               "Ловит ошибку из любого из них и пишет письмо:\n"
               "сценарий, нода, текст ошибки, режим запуска, ID выполнения.",
               40, 60, 520, 220, 3),
        {
            "parameters": {},
            "id": "err-trigger", "name": "Перехват ошибки",
            "type": "n8n-nodes-base.errorTrigger", "typeVersion": 1,
            "position": [60, 360],
        },
        code("Разбор ошибки", ERROR_CODE, 300, 360, "err-parse"),
        {
            "parameters": {
                "fromEmail": FROM_ADDR,
                "toEmail": TO_ADDR,
                "subject": "={{ $json.subject }}",
                "emailFormat": "text",
                "text": "={{ $json.text }}",
                "options": {},
            },
            "id": "err-mail", "name": "Письмо об ошибке",
            "type": "n8n-nodes-base.emailSend", "typeVersion": 2.1,
            "position": [540, 360],
            "credentials": CRED_SMTP,
        },
    ],
    "connections": merge_conns(
        link("Перехват ошибки", "Разбор ошибки"),
        link("Разбор ошибки", "Письмо об ошибке"),
    ),
    "settings": {"executionOrder": "v1", "timezone": "Europe/Moscow"},
}

os.makedirs(OUT, exist_ok=True)
files = [
    ("01-center.json", main, MAIN_ID),
    ("02-sub-search.json", search, SEARCH_ID),
    ("03-sub-mail.json", mail, MAIL_ID),
    ("04-error-workflow.json", error_wf, ERROR_ID),
]
for fname, wf, wid in files:
    wf["id"] = wid
    path = os.path.join(OUT, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, ensure_ascii=False, indent=2)
    print("%-24s %-22s узлов=%d  связей=%d  %d Б"
          % (fname, wid, len(wf["nodes"]),
             sum(len(v["main"][0]) for v in wf["connections"].values() if v["main"][0]),
             os.path.getsize(path)))