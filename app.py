import os
import sqlite3
from datetime import datetime
from io import StringIO
import csv

from flask import Flask, render_template, request, jsonify, g, send_file, abort, current_app
import telebot


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists (for SQLite database)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "requests.db"),
    )

    with app.app_context():
        _init_db()

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            pricing=_get_pricing(),
        )

    @app.route("/contacts")
    def contacts():
        return render_template("contacts.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.post("/api/request")
    def create_request():
        payload = request.get_json(silent=True) or request.form.to_dict()

        name = (payload.get("name") or "").strip()
        phone = (payload.get("phone") or "").strip()
        brand = (payload.get("brand") or "").strip()
        problem = (payload.get("problem") or "").strip()
        preferred_time = (payload.get("preferred_time") or "").strip()

        if not name or not phone:
            return jsonify({"ok": False, "message": "Заполните имя и телефон"}), 400

        try:
            _insert_request(
                name=name,
                phone=phone,
                brand=brand,
                problem=problem,
                preferred_time=preferred_time,
                source_ip=request.headers.get("X-Forwarded-For", request.remote_addr) or "",
                user_agent=request.headers.get("User-Agent", ""),
            )
            
            # Отправка в Telegram бот
            _send_to_telegram(
                name=name,
                phone=phone,
                brand=brand,
                problem=problem,
                preferred_time=preferred_time,
            )
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "message": "Не удалось сохранить заявку"}), 500

        return jsonify({"ok": True, "message": "Заявка отправлена. Мы свяжемся с вами в ближайшее время!"})

    @app.get("/admin/export.csv")
    def export_csv():
        # Optional simple token protection via ?token=... or env ADMIN_TOKEN
        admin_token_env = os.environ.get("ADMIN_TOKEN")
        admin_token_req = request.args.get("token")
        if admin_token_env and admin_token_req != admin_token_env:
            abort(403)

        cur = _get_db().execute(
            """
            SELECT id, name, phone, brand, problem, preferred_time, created_at, source_ip, user_agent
            FROM requests
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "name",
                "phone",
                "brand",
                "problem",
                "preferred_time",
                "created_at",
                "source_ip",
                "user_agent",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["id"],
                    r["name"],
                    r["phone"],
                    r["brand"],
                    r["problem"],
                    r["preferred_time"],
                    r["created_at"],
                    r["source_ip"],
                    r["user_agent"],
                ]
            )
        output.seek(0)
        return send_file(
            output,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}
    
    @app.get("/admin/telegram-info")
    def telegram_info():
        """Вспомогательный эндпоинт для получения информации о Telegram боте"""
        bot_token = "8435619906:AAGjBManY_wA7F9dERiGMWP_vqIfGk4CZNY"
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
        info = {
            "chat_id_from_env": chat_id or "не указан",
            "bot_token": bot_token[:10] + "..." if bot_token else "не указан",
        }
        
        try:
            bot = telebot.TeleBot(bot_token)
            
            # Проверяем бота через get_me
            try:
                bot_info = bot.get_me()
                info["bot_username"] = bot_info.username if bot_info else "неизвестно"
                info["bot_first_name"] = bot_info.first_name if bot_info else "неизвестно"
            except Exception as e:
                info["bot_error"] = str(e)
            
            # Пытаемся получить chat_id через get_updates
            try:
                updates = bot.get_updates()
                if updates:
                    chat_ids = []
                    seen_ids = set()
                    for update in updates:
                        chat_id_found = None
                        chat_name = "неизвестно"
                        
                        if update.message and update.message.chat:
                            chat_id_found = str(update.message.chat.id)
                            chat_name = update.message.chat.first_name or update.message.chat.title or "неизвестно"
                        elif update.edited_message and update.edited_message.chat:
                            chat_id_found = str(update.edited_message.chat.id)
                            chat_name = update.edited_message.chat.first_name or update.edited_message.chat.title or "неизвестно"
                        
                        if chat_id_found and chat_id_found not in seen_ids:
                            seen_ids.add(chat_id_found)
                            chat_ids.append({"id": chat_id_found, "name": chat_name})
                    
                    info["found_chat_ids"] = chat_ids if chat_ids else "не найдено (отправьте сообщение боту)"
                else:
                    info["found_chat_ids"] = "нет обновлений (отправьте сообщение боту)"
            except Exception as e:
                info["updates_error"] = str(e)
                
        except Exception as e:
            info["general_error"] = str(e)
        
        return jsonify(info)

    @app.teardown_appcontext
    def close_db(exc=None):  # noqa: ARG001
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app


# ---------- DB helpers ----------
def _get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def _init_db() -> None:
    conn = _get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            brand TEXT,
            problem TEXT,
            preferred_time TEXT,
            created_at TEXT NOT NULL,
            source_ip TEXT,
            user_agent TEXT
        )
        """
    )
    conn.commit()


def _insert_request(
    *,
    name: str,
    phone: str,
    brand: str,
    problem: str,
    preferred_time: str,
    source_ip: str,
    user_agent: str,
) -> None:
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO requests (name, phone, brand, problem, preferred_time, created_at, source_ip, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            phone,
            brand,
            problem,
            preferred_time,
            datetime.utcnow().isoformat(timespec="seconds") + "Z",
            source_ip,
            user_agent,
        ),
    )
    conn.commit()


def _send_to_telegram(*, name: str, phone: str, brand: str, problem: str, preferred_time: str) -> None:
    """Отправляет заявку в Telegram бот"""
    bot_token = "8435619906:AAGjBManY_wA7F9dERiGMWP_vqIfGk4CZNY"
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "965240931")
    
    try:
        bot = telebot.TeleBot(bot_token)
        
        # Формируем сообщение
        message = f"🔔 <b>Новая заявка с сайта</b>\n\n"
        message += f"👤 <b>Имя:</b> {name}\n"
        message += f"📞 <b>Телефон:</b> {phone}\n"
        if brand:
            message += f"🏷️ <b>Бренд:</b> {brand}\n"
        if problem:
            message += f"🔧 <b>Проблема:</b> {problem}\n"
        if preferred_time:
            message += f"⏰ <b>Удобное время:</b> {preferred_time}\n"
        message += f"\n📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        # Отправляем сообщение
        bot.send_message(chat_id, message, parse_mode="HTML")
        print(f"✅ Заявка успешно отправлена в Telegram (chat_id: {chat_id})")
        
    except telebot.apihelper.ApiTelegramException as e:
        print(f"❌ Ошибка Telegram API: {e}")
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")
        # Игнорируем ошибки отправки в Telegram, чтобы не ломать основной функционал


def _get_pricing():
    # Цены примерные "от", финальная стоимость зависит от модели и диагностики
    return [
        {"component": "Диагностика", "labor_from": 0, "part_from": 0, "total_from": 0},
        {"component": "Компрессор", "labor_from": 4500, "part_from": 12000, "total_from": 16500},
        {"component": "Плата управления", "labor_from": 2500, "part_from": 5000, "total_from": 7500},
        {"component": "Пускозащитное реле", "labor_from": 1200, "part_from": 900, "total_from": 2100},
        {"component": "Термостат", "labor_from": 1500, "part_from": 1200, "total_from": 2700},
        {"component": "Датчик температуры", "labor_from": 1200, "part_from": 700, "total_from": 1900},
        {"component": "Вентилятор испарителя", "labor_from": 1800, "part_from": 1800, "total_from": 3600},
        {"component": "ТЭН оттайки", "labor_from": 2200, "part_from": 1600, "total_from": 3800},
        {"component": "Таймер/модуль оттайки", "labor_from": 1800, "part_from": 1400, "total_from": 3200},
        {"component": "Клапан (No Frost/переключающий)", "labor_from": 1800, "part_from": 1800, "total_from": 3600},
        {"component": "Фильтр-осушитель", "labor_from": 2500, "part_from": 600, "total_from": 3100},
        {"component": "Капиллярная трубка (устранение засора)", "labor_from": 3000, "part_from": 0, "total_from": 3000},
        {"component": "Заправка хладагентом", "labor_from": 2500, "part_from": 1200, "total_from": 3700},
        {"component": "Испаритель (ремонт/замена)", "labor_from": 4000, "part_from": 2500, "total_from": 6500},
        {"component": "Конденсатор", "labor_from": 2200, "part_from": 1500, "total_from": 3700},
        {"component": "Уплотнитель двери", "labor_from": 2000, "part_from": 1800, "total_from": 3800},
        {"component": "Петля/механизм двери", "labor_from": 1500, "part_from": 1000, "total_from": 2500},
        {"component": "Подсветка (лампа/LED модуль)", "labor_from": 700, "part_from": 300, "total_from": 1000},
    ]


app = create_app()


if __name__ == "__main__":
    app.run()


