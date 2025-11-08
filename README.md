# ХолодСервис — ремонт холодильников (Flask + JS + HTML + CSS)

Минималистичный и современный сайт с возможностью оставить заявку, с прайсом по основным комплектующим. Бэкенд на Flask, фронтенд — адаптивная вёрстка.

## Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Способ 1: через flask run
export FLASK_APP=app.py             # Windows PowerShell: $env:FLASK_APP="app.py"
flask run                           # http://127.0.0.1:5000

# Способ 2: напрямую
python app.py
```

## Структура

- `app.py` — приложение Flask, эндпоинты, инициализация SQLite
- `templates/` — Jinja2 шаблоны (`base.html`, `index.html`)
- `static/css/styles.css` — минималистичный адаптивный стиль
- `static/js/app.js` — отправка формы, маска телефона, плавная прокрутка
- `instance/requests.db` — база SQLite создаётся автоматически при первом запуске

## Эндпоинты

- `/` — главная страница
- `POST /api/request` — отправка заявки (JSON): `{ name, phone, brand?, problem?, preferred_time? }`
- `GET /admin/export.csv?token=...` — экспорт заявок в CSV (если указать `ADMIN_TOKEN` в переменных окружения, потребуется токен)
- `/healthz` — healthcheck

## Переменные окружения (опционально)

- `SECRET_KEY` — секретный ключ Flask
- `ADMIN_TOKEN` — токен для `/admin/export.csv`
- `TELEGRAM_CHAT_ID` — ID чата для отправки заявок в Telegram (по умолчанию: `965240931`)

## Заметки

- Прайс является ориентировочным («от»). Конкретная стоимость зависит от модели и результатов диагностики.
- Диагностика бесплатна при выполнении ремонта.


# holremcenter
