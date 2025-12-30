import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------------
# НАСТРОЙКИ
# -----------------------------------

ADMIN_ID = 732055728  # твой Telegram ID

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")
if not SHOP_ID:
    raise RuntimeError("SHOP_ID не найден в .env")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY не найден в .env")

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

# -----------------------------------
# Платёжка ЮKassa
# -----------------------------------

def create_payment(amount: str, description: str) -> Payment:
    payment = Payment.create({
        "amount": {"value": amount, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/your_bot_username"},
        "capture": True,
        "description": description,
    })
    return payment

# -----------------------------------
# Хранилище сообщений
# -----------------------------------

USER_MESSAGES = {}

def remember_message(user_id: int, msg_id: int):
    USER_MESSAGES.setdefault(user_id, []).append(msg_id)

async def cleanup_chat(user_id: int, chat_id: int, bot):
    for msg_id in USER_MESSAGES.get(user_id, []):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass
    USER_MESSAGES[user_id] = []

# -----------------------------------
# Отзывы
# -----------------------------------

REVIEWS_FILE = "reviews.json"

def load_reviews():
    if not os.path.exists(REVIEWS_FILE):
        return []
    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_reviews(reviews):
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

def add_review(review):
    reviews = load_reviews()
    reviews.append(review)
    save_reviews(reviews)

# -----------------------------------
# Клавиатуры
# -----------------------------------

def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📱 Приложение"],
            ["📸 Что вы увидите"],
            ["📘 Инструкция"],
            ["⭐ Отзывы", "📝 Оставить отзыв"],
            ["💳 Купить экскурсию"],
            ["ℹ️ О проекте"],
        ],
        resize_keyboard=True,
    )# -----------------------------------
# /start
# -----------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в аудиогид по Казани.",
        reply_markup=get_main_menu(),
    )
    remember_message(user.id, msg.message_id)

# -----------------------------------
# /admin — доступ только для ADMIN_ID
# -----------------------------------

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("У вас нет доступа.")
        return

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔐 Открыть мини‑апп (админ)",
                web_app=WebAppInfo(
                    url="https://gospodeensobaka-afk.github.io/kazan-audioguide/index.html"
                )
            )
        ]
    ])

    await update.message.reply_text(
        "Админ‑панель:",
        reply_markup=kb
    )

# -----------------------------------
# Команда удаления отзыва /del <ID>
# -----------------------------------

async def admin_delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Использование: /del <ID>")
        return

    try:
        idx = int(context.args[0])
    except:
        await update.message.reply_text("ID должен быть числом.")
        return

    reviews = load_reviews()

    if idx < 0 or idx >= len(reviews):
        await update.message.reply_text("Нет такого ID.")
        return

    deleted = reviews.pop(idx)
    save_reviews(reviews)

    await update.message.reply_text(
        f"Удалено:\n⭐ {deleted['rating']}\n{deleted['text']}"
    )

# -----------------------------------
# Обработчик текстовых сообщений
# -----------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot = context.bot    # -----------------------------------
    # 📱 Приложение
    # -----------------------------------
    if text == "📱 Приложение":
        msg = await bot.send_message(
            chat_id=chat_id,
            text="Здесь позже появится кнопка для запуска мини‑приложения.",
            reply_markup=get_main_menu(),
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 📸 Что вы увидите
    # -----------------------------------
    elif text == "📸 Что вы увидите":
        descriptions = [
            "Зимняя Казань — свет, масштаб и атмосфера.",
            "Панорамные виды города.",
            "Архитектурные шедевры.",
            "Сказочный финал маршрута.",
        ]
        files = ["images/view1.jpg", "images/view2.jpg", "images/view3.jpg", "images/view4.jpg"]

        for path, desc in zip(files, descriptions):
            try:
                photo_msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=open(path, "rb"),
                    caption=desc
                )
                remember_message(user_id, photo_msg.message_id)
            except:
                msg = await bot.send_message(chat_id=chat_id, text=desc)
                remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 📘 Инструкция
    # -----------------------------------
    elif text == "📘 Инструкция":
        instruction = (
            "📘 *Инструкция*\n\n"
            "Это аудиогид, который ведёт вас по Казани в формате «от точки к точке».\n"
            "Вы едете в машине, а приложение автоматически включает аудио, когда вы подъезжаете к нужному месту.\n\n"
            "Чтобы всё прошло идеально:\n"
            "1. Вам нужен смартфон с интернетом.\n"
            "2. Подключите телефон к машине по Bluetooth — так звук будет громким и чистым.\n"
            "3. Купите экскурсию в боте.\n"
            "4. Нажмите кнопку «Приложение» — откроется маршрут.\n"
            "5. Стартовая точка: остановка возле часов на улице Баумана.\n"
            "6. Просто следуйте по дороге — аудио включается само.\n\n"
            "Если что‑то пойдёт не так — пишите мне: 8‑951‑061‑35‑64"
        )

        msg = await bot.send_message(
            chat_id=chat_id,
            text=instruction,
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # ⭐ Отзывы
    # -----------------------------------
    elif text == "⭐ Отзывы":
        reviews = load_reviews()

        if not reviews:
            msg = await bot.send_message(
                chat_id=chat_id,
                text="Пока нет отзывов.",
                reply_markup=get_main_menu()
            )
            remember_message(user_id, msg.message_id)
            return

        for i, r in enumerate(reviews):
            username = r["username"] or f"id{r['user_id']}"
            stars = "⭐" * r["rating"]

            msg = await bot.send_message(
                chat_id=chat_id,
                text=f"ID {i}\n{stars}\n@{username}\n\n{r['text']}",
                reply_markup=get_main_menu(),
            )
            remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 📝 Оставить отзыв — шаг 1
    # -----------------------------------
    elif text == "📝 Оставить отзыв":
        context.user_data["review_mode"] = "rating"
        msg = await bot.send_message(
            chat_id=chat_id,
            text="Оцените экскурсию от 1 до 5 ⭐",
            reply_markup=ReplyKeyboardMarkup(
                [["1", "2", "3", "4", "5"], ["🔙 В главное меню"]],
                resize_keyboard=True,
            ),
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 📝 Оставить отзыв — шаг 2
    # -----------------------------------
    elif context.user_data.get("review_mode") == "rating" and text in ["1", "2", "3", "4", "5"]:
        context.user_data["review_rating"] = int(text)
        context.user_data["review_mode"] = "text"

        msg = await bot.send_message(
            chat_id=chat_id,
            text="Напишите ваш отзыв:",
            reply_markup=ReplyKeyboardMarkup([["🔙 В главное меню"]], resize_keyboard=True),
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 📝 Оставить отзыв — шаг 3
    # -----------------------------------
    elif context.user_data.get("review_mode") == "text":
        rating = context.user_data.get("review_rating")
        review_text = text

        review = {
            "user_id": user_id,
            "username": update.effective_user.username,
            "rating": rating,
            "text": review_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        add_review(review)

        context.user_data["review_mode"] = None
        context.user_data["review_rating"] = None

        msg = await bot.send_message(
            chat_id=chat_id,
            text="Спасибо за отзыв! 🙌",
            reply_markup=get_main_menu()
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # 💳 Купить экскурсию
    # -----------------------------------
    elif text == "💳 Купить экскурсию":
        caption = (
            "🎧 *Зимняя Казань*\n"
            "Цена: 10 ₽\n\n"
            "• Автовоспроизведение по GPS\n"
            "• Профессиональный голос\n"
            "• Доступ сразу\n"
        )

        try:
            photo_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=open("tovar/tovar.jpg", "rb"),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [["✅ Оплатить 10 ₽"], ["🔙 В главное меню"]],
                    resize_keyboard=True,
                ),
            )
            remember_message(user_id, photo_msg.message_id)
        except:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [["✅ Оплатить 10 ₽"], ["🔙 В главное меню"]],
                    resize_keyboard=True,
                ),
            )
            remember_message(user_id, msg.message_id)    # -----------------------------------
    # Оплата
    # -----------------------------------
    elif text == "✅ Оплатить 10 ₽":
        description = f"Зимняя Казань chat_id={chat_id}"

        try:
            payment = create_payment("10.00", description)
            pay_url = payment.confirmation.confirmation_url

            msg = await bot.send_message(
                chat_id=chat_id,
                text=f"Ссылка для оплаты:\n{pay_url}",
                reply_markup=get_main_menu(),
            )
            remember_message(user_id, msg.message_id)
        except:
            msg = await bot.send_message(
                chat_id=chat_id,
                text="Ошибка при создании платежа.",
                reply_markup=get_main_menu()
            )
            remember_message(user_id, msg.message_id)

    # -----------------------------------
    # ℹ️ О проекте
    # -----------------------------------
    elif text == "ℹ️ О проекте":
        about = (
            "ℹ️ *О проекте*\n\n"
            "Этот аудиогид — мой личный проект о Казани.\n"
            "Я живу здесь и собрал маршрут так, чтобы вы увидели не только «открыточные» места, "
            "но и настоящую атмосферу города.\n\n"
            "Маршрут создан для поездки на машине: вы просто едете, а аудио включается автоматически.\n\n"
            "Я хочу, чтобы вы почувствовали Казань так, как чувствуют её местные: "
            "свет, архитектура, уютные улицы, неожиданные виды и истории.\n\n"
            "Спасибо, что поддерживаете локальные проекты ❤️"
        )

        msg = await bot.send_message(
            chat_id=chat_id,
            text=about,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # Назад
    # -----------------------------------
    elif text == "🔙 В главное меню":
        msg = await bot.send_message(
            chat_id=chat_id,
            text="Главное меню:",
            reply_markup=get_main_menu()
        )
        remember_message(user_id, msg.message_id)

    # -----------------------------------
    # Неизвестная команда
    # -----------------------------------
    else:
        msg = await bot.send_message(
            chat_id=chat_id,
            text="Неизвестная команда.",
            reply_markup=get_main_menu()
        )
        remember_message(user_id, msg.message_id)

# -----------------------------------
# Запуск бота
# -----------------------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))   # ← новая команда
    app.add_handler(CommandHandler("del", admin_delete_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
