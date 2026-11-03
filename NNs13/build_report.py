"""Сборка отчёта NNs13.docx по уроку 13.

Запуск: <python> build_report.py
Результат: n8n-lab/hw13/NNs13.docx
"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
SHOTS = BASE / "shots"
OUT = BASE / "NNs13.docx"

USABLE_WIDTH_CM = 17.0


def set_cell_background(cell, hex_color):
    """Заливка ячейки — нужна для шапки таблиц."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.makeelement(qn("w:shd"), {
        qn("w:val"): "clear",
        qn("w:color"): "auto",
        qn("w:fill"): hex_color,
    })
    tc_pr.append(shd)


def add_table(document, headers, rows, widths_cm, font_size=9, header_fill="E8EEF7"):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(font_size)
        set_cell_background(hdr[i], header_fill)

    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(text))
            run.font.size = Pt(font_size)

    for row in table.rows:
        for i, width in enumerate(widths_cm):
            row.cells[i].width = Cm(width)

    document.add_paragraph()
    return table


def add_caption(document, text):
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    return p


def add_picture(document, filename, caption, width_cm=16.0):
    path = SHOTS / filename
    if not path.exists():
        raise FileNotFoundError(f"нет файла скриншота: {path}")
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    add_caption(document, caption)


def add_mono_block(document, text):
    for line in text.strip("\n").split("\n"):
        p = document.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.8)
        run = p.add_run(line if line else " ")
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        run.font.size = Pt(8.5)
    document.add_paragraph()


def main():
    document = Document()

    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

    core = document.core_properties
    core.author = "n8n lab"
    core.last_modified_by = "n8n lab"
    core.title = "Урок 13. Финал модуля. Центр автоматизации"
    core.subject = "n8n, автоматизация, Subworkflow, Error Workflow"
    core.comments = "Вариант 1 (Базовый)"

    # --- титул ---
    title = document.add_heading("Урок 13. Финал модуля. Центр автоматизации", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = document.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("Вариант 1 (Базовый) — отчёт о выполнении практики")
    run.font.size = Pt(12)
    run.bold = True

    meta = document.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(
        "n8n 2.27.5 (self-hosted, Docker) · часовой пояс Europe/Moscow · "
        "дата отчёта 02.11.2026"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # --- 1 ---
    document.add_heading("1. Задание и результат", level=1)
    document.add_paragraph(
        "Нужно было собрать центр автоматизации: основной сценарий вызывает Subworkflow, "
        "Subworkflow опубликован, есть Error Workflow с Error Trigger и узлом уведомления, "
        "Error Workflow привязан через настройки сценария, есть запуск по расписанию. "
        "Проверить ручной запуск, запуск по расписанию и намеренную ошибку с уведомлением."
    )
    add_table(
        document,
        ["Пункт задания", "Как выполнено", "Где смотреть"],
        [
            ["Основной сценарий с вызовом Subworkflow",
             "Hw13CenterAuto01, 11 узлов, 9 связей. Два узла Execute Workflow: «Поиск в базе» и «Отправка на почту»",
             "workflows/01-center.json"],
            ["Subworkflow опубликован",
             "Hw13SearchKb0001 и Hw13SendMail001 в статусе Published",
             "Скриншот 02"],
            ["Error Workflow: Error Trigger + уведомление",
             "Hw13ErrorHook001: errorTrigger → Code «Разбор ошибки» → emailSend",
             "workflows/04-error-workflow.json"],
            ["Error Workflow привязан через настройки",
             "settings.errorWorkflow = Hw13ErrorHook001 у основного сценария и обоих Subworkflow",
             "Скриншот 04"],
            ["Расписание",
             "Schedule Trigger: каждые 1 день, 09:00, Europe/Moscow",
             "Скриншот 05"],
            ["Ручной запуск",
             "Выполнение #143, success, 2.899 с, получен ответ по базе знаний",
             "Скриншот 06"],
            ["Запуск по расписанию",
             "Выполнения #137 и #140, режим trigger, success",
             "Скриншот 07"],
            ["Намеренная ошибка и уведомление",
             "Остановлен Qdrant → выполнения #133 и #134 со статусом error → два письма",
             "Скриншот 08"],
        ],
        [4.6, 9.2, 3.2],
    )

    # --- 2 ---
    document.add_heading("2. Состав центра автоматизации", level=1)
    document.add_paragraph(
        "Центр состоит из четырёх сценариев: одного основного, двух переиспользуемых "
        "Subworkflow и одного Error Workflow. Все четыре опубликованы."
    )
    add_table(
        document,
        ["Сценарий", "ID", "Узлов", "Роль", "Статус"],
        [
            ["Урок 13 — Центр автоматизации", "Hw13CenterAuto01", "11",
             "Основной: две точки входа, развилка, вызовы Subworkflow", "Published"],
            ["Урок 13 — Subworkflow «Поиск в базе»", "Hw13SearchKb0001", "7",
             "Вопрос → эмбеддинг → Qdrant → готовый контекст", "Published"],
            ["Урок 13 — Subworkflow «Отправка результата на почту»", "Hw13SendMail001", "5",
             "Готовый ответ → письмо", "Published"],
            ["Урок 13 — Error Workflow", "Hw13ErrorHook001", "4",
             "Перехват ошибки → письмо администратору", "Published"],
        ],
        [5.2, 3.4, 1.4, 5.4, 1.6],
    )

    # --- 3 ---
    document.add_heading("3. Основной сценарий", level=1)
    document.add_paragraph(
        "Сценарий Hw13CenterAuto01 сводит две точки входа в один поток и выносит "
        "поиск и отправку письма в переиспользуемые Subworkflow."
    )
    add_table(
        document,
        ["№", "Узел", "Тип", "Что делает"],
        [
            ["1", "Чат", "chatTrigger v1.4",
             "Точка входа 1: сообщение в чате, публичный вебхук center-hw13-chat"],
            ["2", "Расписание", "scheduleTrigger v1.3", "Точка входа 2: ежедневно в 09:00"],
            ["3", "Единая точка входа", "code v2",
             "Развилка: есть chatInput — берём его, иначе фиксированный вопрос. Отдаёт {query, source}"],
            ["4", "Поиск в базе", "executeWorkflow v1.3",
             "Вызов Subworkflow Hw13SearchKb0001"],
            ["5", "Подготовка токена", "code v2", "Генерирует RqUID для запроса токена"],
            ["6", "Токен GigaChat", "httpRequest v4.2",
             "OAuth GigaChat, form-urlencoded, scope GIGACHAT_API_PERS"],
            ["7", "Ответ GigaChat", "httpRequest v4.2",
             "Запрос к /api/v1/chat/completions с контекстом из Subworkflow"],
            ["8", "Разбор ответа", "code v2", "Достаёт текст ответа модели"],
            ["9", "Отправка на почту", "executeWorkflow v1.3",
             "Вызов Subworkflow Hw13SendMail001"],
            ["10", "Ответ в чат", "code v2",
             "Возвращает {output} из «Разбор ответа», чтобы вывод почтового Subworkflow не попал в чат"],
        ],
        [1.0, 3.6, 3.4, 9.0],
    )
    document.add_paragraph(
        "Развилка «Единая точка входа» обязательна: у сценария два триггера. Чат передаёт chatInput, "
        "расписание не передаёт ничего — без развилки запуск по расписанию падал бы на пустом запросе. "
        "Узел «Ответ в чат» стоит после почтового Subworkflow и читает текст из «Разбор ответа», "
        "иначе интерфейс чата показал бы служебный вывод отправки письма."
    )

    # --- 4 ---
    document.add_heading("4. Subworkflow «Поиск в базе»", level=1)
    document.add_paragraph(
        "Сценарий Hw13SearchKb0001 забирает контекст из векторной базы и отдаёт его вызывающему "
        "сценарию. Вход — query, выход — query, found, hits, top_score, context."
    )
    add_table(
        document,
        ["Узел", "Тип", "Что делает"],
        [
            ["Старт поиска", "executeWorkflowTrigger v1.2", "Вход passthrough — принимает данные вызова"],
            ["Подготовка запроса", "code v2", "Нормализует вопрос"],
            ["Эмбеддинги вопроса", "httpRequest v4.2",
             "ProxyAPI, text-embedding-3-small, 1536 измерений"],
            ["Сборка запроса", "code v2", "Собирает тело запроса к Qdrant, id точек — UUID"],
            ["Поиск в Qdrant", "httpRequest v4.2", "Коллекция n8n-lab-kb, limit 4, with_payload"],
            ["Подготовка контекста", "code v2", "Склеивает найденные фрагменты в один контекст"],
        ],
        [4.4, 4.4, 8.2],
    )

    # --- 5 ---
    document.add_heading("5. Subworkflow «Отправка результата на почту»", level=1)
    document.add_paragraph(
        "Сценарий Hw13SendMail001 принимает адрес, тему и тело письма. Вынесен отдельно, "
        "чтобы отправку можно было использовать и в других сценариях."
    )
    add_table(
        document,
        ["Узел", "Тип", "Что делает"],
        [
            ["Старт отправки", "executeWorkflowTrigger v1.2", "Вход passthrough"],
            ["Подготовка письма", "code v2", "Берёт to, subject, mail_body (или text)"],
            ["Письмо", "emailSend v2.1", "Отправка через SMTP mailpit-lab"],
            ["Итог отправки", "code v2", "Возвращает статус отправки"],
        ],
        [4.4, 4.4, 8.2],
    )

    # --- 6 ---
    document.add_heading("6. Error Workflow", level=1)
    document.add_paragraph(
        "Сценарий Hw13ErrorHook001 запускается не по расписанию и не по вебхуку, а по факту сбоя "
        "другого сценария. Внутри три рабочих узла."
    )
    add_table(
        document,
        ["Узел", "Тип", "Что делает"],
        [
            ["Перехват ошибки", "errorTrigger v1", "Получает от n8n объект ошибки"],
            ["Разбор ошибки", "code v2",
             "Собирает тему и текст письма: сценарий, нода, текст ошибки, режим запуска, ID выполнения"],
            ["Письмо об ошибке", "emailSend v2.1", "Письмо на owner@n8n-lab.local"],
        ],
        [4.4, 4.4, 8.2],
    )
    document.add_paragraph("Пример реального письма, полученного при проверке:")
    add_mono_block(
        document,
        """
Тема: Сбой автоматизации: Урок 13 — Центр автоматизации

Сценарий: Урок 13 — Центр автоматизации
Нода со сбоем: Поиск в Qdrant
Ошибка: The DNS server returned an error, perhaps the server is offline
Режим запуска: webhook
ID выполнения: 133
Время: 01.11.2026, 22:56:08

Откройте Executions в n8n и найдите выполнение 133.
        """,
    )

    # --- 7 ---
    document.add_heading("7. Привязка Error Workflow через настройки", level=1)
    document.add_paragraph(
        "Привязка сделана штатно — через поле Error Workflow в настройках сценария, а не "
        "отдельным узлом. Значение хранится в settings.errorWorkflow."
    )
    add_table(
        document,
        ["Сценарий", "Привязка к Error Workflow", "Комментарий"],
        [
            ["Hw13CenterAuto01", "Hw13ErrorHook001", "Основной сценарий — уведомление о сбое"],
            ["Hw13SearchKb0001", "Hw13ErrorHook001", "Subworkflow — уведомление о сбое поиска"],
            ["Hw13SendMail001", "Hw13ErrorHook001", "Subworkflow — уведомление о сбое отправки"],
            ["Hw13ErrorHook001", "не задана", "Сам на себя не ссылается, иначе возможен цикл"],
        ],
        [4.6, 5.0, 7.4],
    )
    document.add_paragraph(
        "Привязка к Subworkflow даёт отдельное письмо, когда падает именно поиск: в этом случае "
        "приходят два уведомления — от Subworkflow и от основного сценария, который на нём упал. "
        "В каждом письме свой ID выполнения, поэтому разбираться удобно."
    )

    # --- 8 ---
    document.add_heading("8. Расписание", level=1)
    add_table(
        document,
        ["Параметр", "Значение"],
        [
            ["Тип интервала", "Days"],
            ["Каждые", "1 день"],
            ["Час запуска", "09:00"],
            ["Минута", "0"],
            ["Часовой пояс сценария", "Europe/Moscow"],
        ],
        [7.0, 10.0],
    )
    document.add_paragraph(
        "Расписание и чат ведут в один и тот же узел «Единая точка входа». При запуске по расписанию "
        "chatInput пустой, поэтому развилка подставляет фиксированный вопрос "
        "«Какие условия возврата товара надлежащего качества?» — так ежедневный запуск проверяет "
        "всю цепочку без участия человека."
    )

    # --- 9 ---
    document.add_heading("9. Проверки", level=1)
    add_table(
        document,
        ["Проверка", "Что делал", "Результат"],
        [
            ["Ручной запуск",
             "Вопрос в чате: «Сколько дней даётся на возврат товара надлежащего качества?»",
             "Выполнение #143, success, 2.899 с. Ответ про 14 дней, заводскую упаковку, чек и возврат денег за 10 рабочих дней"],
            ["Вопрос вне базы", "«Вы доставляете кофемашины в Казахстан?»",
             "Ответ «В базе знаний нет информации по данному запросу» — защита от выдумывания работает"],
            ["Запуск по расписанию",
             "Временно поставил интервал 1 минута, дождался автоматических запусков, вернул 09:00",
             "Выполнения #137 (22:58:07) и #140 (22:59:07), режим trigger, status success"],
            ["Намеренная ошибка",
             "Остановил контейнер qdrant-lab, отправил вопрос, затем поднял контейнер обратно",
             "Выполнения #133 (webhook) и #134 (integrated) со статусом error; два письма с нодой «Поиск в Qdrant»"],
        ],
        [3.0, 7.4, 6.6],
    )

    # --- 10 ---
    document.add_heading("10. Скриншоты", level=1)
    add_picture(document, "01-center-canvas.png",
                "Скриншот 1. Основной сценарий целиком: два триггера, развилка, оба вызова Subworkflow, "
                "GigaChat, почта и ответ в чат")
    add_picture(document, "02-subworkflow-published.png",
                "Скриншот 2. Subworkflow «Поиск в базе» в статусе Published")
    add_picture(document, "03-error-workflow.png",
                "Скриншот 3. Error Workflow: Error Trigger → разбор ошибки → письмо")
    add_picture(document, "04-settings-error-workflow.png",
                "Скриншот 4. Настройки основного сценария: поле Error Workflow заполнено")
    add_picture(document, "05-schedule-trigger.png",
                "Скриншот 5. Параметры Schedule Trigger: интервал Days, час 9, минута 0")
    add_picture(document, "06-execution-143.png",
                "Скриншот 6. Ручной запуск #143: вопрос в чате, ответ и выход ноды «Ответ в чат»")
    add_picture(document, "07-executions-list.png",
                "Скриншот 7. История выполнений: ручной запуск, запуски по расписанию, "
                "срабатывания Error Workflow и ошибка")
    add_picture(document, "08-error-email.png",
                "Скриншот 8. Письмо о сбое в mailpit: сценарий, нода, ошибка, режим и ID выполнения")

    # --- 11 ---
    document.add_heading("11. Что пришлось починить по дороге", level=1)
    document.add_paragraph(
        "Ключ GigaChat в подключении n8n оказался просроченным. OAuth отвечал 401, n8n показывал "
        "«Authorization failed — please check your credentials». Из-за этого перестал работать и "
        "сценарий урока 12. Подключение GigaChat — ключ авторизации (RAG) обновлено новым ключом, "
        "после чего урок 12 снова отвечает.", style="List Number")
    document.add_paragraph(
        "Тело запроса к GigaChat ломало JSON: контекст из Qdrant содержит переводы строк, а они "
        "недопустимы внутри строкового литерала JSON. Ошибка выглядела как "
        "«Bad control character in string literal in JSON at position 456». Тело переведено на "
        "JSON.stringify.", style="List Number")
    document.add_paragraph(
        "Импорт сценариев подхватывал старую версию файла: в контейнере нельзя удалить прежний "
        "каталог, поэтому импорт читал уже лежавшие там файлы. Импорт переведён на новый каталог "
        "при каждой итерации.", style="List Number")

    # --- 12 ---
    document.add_heading("12. Честные оговорки", level=1)
    document.add_paragraph(
        "Расписание проверено ускорением. Ждать 09:00 живьём бессмысленно, поэтому интервал временно "
        "переключался на одну минуту: автоматические запуски получены и зафиксированы, после чего "
        "расписание возвращено на «каждый день в 09:00». На скриншоте 5 — именно итоговая настройка.",
        style="List Bullet")
    document.add_paragraph(
        "Ошибка проверена настоящая, а не имитация: я останавливал контейнер Qdrant, а не подменял "
        "адрес. Сообщение «DNS server returned an error» — подлинный ответ сети, после проверки "
        "контейнер поднят обратно.", style="List Bullet")
    document.add_paragraph(
        "Почта — локальный mailpit, а не реальная доставка. Письма проверены через API mailpit и "
        "его веб-интерфейс.", style="List Bullet")
    document.add_paragraph(
        "Для съёмки скриншотов требовался вход в интерфейс n8n. Присланный пароль сервер не принял "
        "(401), поэтому пароль владельца временно заменялся служебным. После съёмки исходный хеш "
        "восстановлен из резерва, служебный пароль проверен — теперь он даёт 401. Резервные копии "
        "удалены.", style="List Bullet")
    document.add_paragraph(
        "Эмбеддинги GigaChat на текущем ключе по-прежнему недоступны (402 Payment Required для всех "
        "моделей эмбеддингов), поэтому в Subworkflow используются эмбеддинги ProxyAPI — как и в "
        "уроке 12.", style="List Bullet")

    # --- 13 ---
    document.add_heading("13. Рекомендации по безопасности", level=1)
    document.add_paragraph(
        "Ключи и пароли, попавшие в переписку, стоит перевыпустить: пароль приложения Яндекс, оба "
        "ключа ProxyAPI и ключ GigaChat. Все они передавались в чат в открытом виде."
    )

    # --- 14 ---
    document.add_heading("14. Файлы", level=1)
    add_table(
        document,
        ["Файл", "Назначение"],
        [
            ["NNs13.docx", "Этот отчёт"],
            ["README.md", "Текстовое описание работы"],
            ["workflows/01-center.json", "Основной сценарий"],
            ["workflows/02-sub-search.json", "Subworkflow «Поиск в базе»"],
            ["workflows/03-sub-mail.json", "Subworkflow «Отправка результата на почту»"],
            ["workflows/04-error-workflow.json", "Error Workflow"],
            ["build_workflows.py", "Генератор JSON сценариев"],
            ["shots/*.png", "Скриншоты 1–8"],
        ],
        [6.4, 10.6],
    )

    document.save(OUT)
    print(f"сохранено: {OUT} ({OUT.stat().st_size} Б)")


if __name__ == "__main__":
    main()