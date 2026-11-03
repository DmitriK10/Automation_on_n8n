# NNs10 — бэкап и восстановление n8n

Домашнее задание урока 10, вариант 1 (базовый). Здесь — комплект бэкапа self-hosted
n8n, проверка копии и восстановление рабочего инстанса на отдельном порту.

## Что в папке

| Файл | Что это |
|---|---|
| `NNs10.docx` | отчёт по заданию: что бэкапили, как проверяли, как восстанавливали; все скриншоты внутри |
| `README.md` | этот файл: как устроен бэкап, как развернуть и проверить |
| `workflow-Hw09ZayavkaPay01-2026-11-01.json` | выгрузка сценария кнопкой Download; дата в имени добавлена при раскладке |

Скриншоты отдельными файлами не сдаются — десять рисунков вложены в сам отчёт
и идут по тексту с подписями. Файлов `.env`, `config` и баз данных здесь нет —
по требованию задания они не прикладываются.

## Стенд

| Компонент | Версия | Порт | Контейнер |
|---|---|---|---|
| n8n | `n8nio/n8n:2.27.5` | 5678 | `n8n-lab` |
| NocoDB | `nocodb/nocodb:2026.09.1` | 8080 | `nocodb-lab` |
| восстановленный n8n | `n8nio/n8n:2.27.5` | 5680 | `n8n-restore` |

Порты привязаны к `127.0.0.1` сервера, снаружи — только через SSH-туннель.

## Что входит в комплект бэкапа

Комплект собран под одной меткой времени `2026-11-01_0200`, папка `~/backup`
на сервере, всего 7,0 МБ:

| Файл | Размер | Что внутри |
|---|---|---|
| `n8n-db-2026-11-01_0200.sqlite` | 2 854 912 Б | вся база n8n: 9 сценариев, 8 подключений, 50 запусков |
| `config-2026-11-01_0200` | 88 Б | файл `config` с ключом шифрования |
| `env-2026-11-01_0200` | 605 Б | 19 переменных окружения контейнера, включая `N8N_ENCRYPTION_KEY` |
| `nocodb-2026-11-01_0200.sqlite` | 4 251 648 Б | база NocoDB, 182 таблицы |
| `workflow-Hw09ZayavkaPay01-2026-11-01_0200.json` | 31 938 Б | один сценарий, выгруженный через интерфейс |
| `all-workflows-2026-11-01_0200.json` | 66 637 Б | все 9 сценариев одним файлом |
| `workflows/` | 9 файлов | те же сценарии по отдельности |

Ключ шифрования — не формальность: подключения внутри базы зашифрованы именно им.
Без правильного ключа база открывается, а подключения — нет.

## Как снять такой бэкап

```bash
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p ~/backup

# база n8n: транзакционный снимок, а не cp — база работает в режиме WAL
sqlite3 ~/.n8n/database.sqlite ".backup ~/backup/n8n-db-$STAMP.sqlite"

# ключ шифрования и окружение
cp ~/.n8n/config ~/backup/config-$STAMP
docker exec n8n-lab env | sort > ~/backup/env-$STAMP
chmod 600 ~/backup/config-$STAMP ~/backup/env-$STAMP

# база NocoDB
sqlite3 ~/nocodb/noco.db ".backup ~/backup/nocodb-$STAMP.sqlite"

# сценарии: один — руками через Download в интерфейсе, все — командой
docker exec -u 0 n8n-lab mkdir -p /tmp/wfout
docker exec -u 0 n8n-lab chown node:node /tmp/wfout
docker exec n8n-lab n8n export:workflow --all --separate --output=/tmp/wfout/
docker cp n8n-lab:/tmp/wfout/. ~/backup/workflows/
```

`~/.n8n` и `~/nocodb` на этом сервере — симлинки на тома Docker
(`/var/lib/docker/volumes/n8n-lab-n8n-data/_data` и
`/var/lib/docker/volumes/n8n-lab-nocodb-data/_data`).

## Как проверить бэкап

Копию открываем в режиме `immutable`, иначе SQLite создаст рядом служебные файлы:

```bash
sqlite3 "file:~/backup/n8n-db-$STAMP.sqlite?immutable=1" "select count(*) from workflow_entity;"
sqlite3 -readonly ~/.n8n/database.sqlite "select count(*) from workflow_entity;"   # для сверки
sqlite3 "file:~/backup/n8n-db-$STAMP.sqlite?immutable=1" "pragma integrity_check;"
sqlite3 "file:~/backup/nocodb-$STAMP.sqlite?immutable=1" ".tables" | wc -w
sqlite3 "file:~/backup/nocodb-$STAMP.sqlite?immutable=1" "pragma integrity_check;"
```

Сверка на этом комплекте:

| Что сверяем | Рабочий инстанс | Копия |
|---|---|---|
| сценарии | 9 | 9 |
| подключения | 8 | 8 |
| запуски | 50 | 50 |
| таблицы NocoDB | 182 | 182 |
| `integrity_check` | ok | ok |

Про таблицы NocoDB: `select count(*) from sqlite_master where type='table'` даёт 183,
потому что считает и служебную `sqlite_sequence`. Реальных таблиц — 182, и именно
это число показывает `sqlite3 .tables` на скриншоте проверки.

## Как восстановить на другом порту

```bash
STAMP=2026-11-01_0200
mkdir -p ~/restore-test/.n8n
cp ~/backup/n8n-db-$STAMP.sqlite ~/restore-test/.n8n/database.sqlite
cp ~/backup/config-$STAMP        ~/restore-test/.n8n/config
cp ~/backup/env-$STAMP           ~/restore-test/.n8n/.env
chmod 600 ~/restore-test/.n8n/config ~/restore-test/.n8n/.env
chown -R 1000:1000 ~/restore-test

docker run -d --name n8n-restore -p 127.0.0.1:5680:5678 \
  -v ~/restore-test/.n8n:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  -e GENERIC_TIMEZONE=Europe/Moscow \
  -e TZ=Europe/Moscow \
  n8nio/n8n:2.27.5

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5680/healthz   # 200
```

Имена файлов обязаны вернуться к тем, что ждёт n8n: `database.sqlite`, `config`,
`.env`. Рабочий инстанс на 5678 при этом не останавливается — оба работают
одновременно.

Проверка, что ключ подошёл (это и есть настоящая проверка комплекта):

```bash
docker exec n8n-restore n8n export:credentials --all --output=/tmp/co/c.json
# Successfully exported 8 credentials.
```

Если ключ не тот, выгрузка подключений упадёт или вернёт пустоту.

Смотреть восстановленный инстанс — через туннель:

```bash
ssh -N -L 5680:127.0.0.1:5680 root@<сервер>
# затем http://localhost:5680
```

Убрать за собой:

```bash
docker rm -f n8n-restore
rm -rf ~/restore-test
```

## Грабли, на которые легко наступить

- **`cp database.sqlite` даёт неполный бэкап.** База в режиме WAL: рядом лежит
  журнал `database.sqlite-wal`, и в нём может быть больше данных, чем в основном
  файле (на этом стенде 4,0 МБ против 2,7 МБ). Нужен `sqlite3 ".backup"`.
- **Без `config` и `N8N_ENCRYPTION_KEY` подключения не расшифруются.** Ключ
  обязан быть тем же, что в рабочем инстансе; в `env` он должен быть настоящим.
- **`n8n export:workflow` падает с `EACCES`**, если папка вывода принадлежит
  root: процесс в контейнере работает от пользователя `node`. Лечится
  `docker exec -u 0 … chown node:node`.
- **Не открывайте копию в режиме `mode=ro`** — рядом появятся `-shm`/`-wal`.
  Для проверки используйте `?immutable=1`.
- **`find ~ -name noco.db` ничего не найдёт**, если путь — симлинк на том Docker.
  Ищите от корня: `find / -name noco.db`.

## Чего в этой папке нет

Самих файлов базы, `config` и `.env` — по требованию задания. Ключ шифрования,
пароли и токены в отчёт и README не переносились.