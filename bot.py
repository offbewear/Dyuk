import os
import sqlite3
import qrcode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─────────────────────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────────────────────
# ВАЖНО: старый токен «засветился», обязательно создай новый в @BotFather
# и положи его в переменную окружения BOT_TOKEN (export BOT_TOKEN="...").
TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_НОВЫЙ_ТОКЕН")
ADMIN_ID = 1880492159

TZ = "+5 hours"                 # часовой пояс Узбекистана для datetime() в SQL
CUPS_FOR_FREE = 7               # сколько чашек до бесплатной
FIRST_ORDER_DISCOUNT = 0.20     # скидка на первый заказ (20%)
INACTIVE_DAYS = 7               # через сколько дней молчания напомнить о себе
LACTOSE_FREE_PRICE = 10000
SYRUP_PRICE = 5000


def fmt(n: int) -> str:
    """25000 -> '25 000'"""
    return f"{n:,}".replace(",", " ")


# ─────────────────────────────────────────────────────────────
# МЕНЮ  (категория -> напиток -> размеры/цены)
# customizable=False  ->  только размер, без молока/сахара/сиропа
# ─────────────────────────────────────────────────────────────
MENU = {
    "hot": {
        "title": "☕ Горячий кофе",
        "drinks": {
            "cappuccino":  {"name": "Капучино",          "sizes": {"M": 25000, "L": 27000}, "custom": True},
            "latte":       {"name": "Латте",             "sizes": {"M": 27000, "L": 30000}, "custom": True},
            "americano":   {"name": "Американо",         "sizes": {"M": 22000, "L": 25000}, "custom": True},
            "raf":         {"name": "Раф",               "sizes": {"M": 28000, "L": 32000}, "custom": True},
            "raf_cream":   {"name": "Раф на сливках",    "sizes": {"M": 35000, "L": 55000}, "custom": True},
            "bek_mokko":   {"name": "Бек мокко",         "sizes": {"M": 28000, "L": 32000}, "custom": True},
            "flat_white":  {"name": "Флэт вайт",         "sizes": {"M": 30000, "L": 33000}, "custom": True},
            "cacao":       {"name": "Какао",             "sizes": {"M": 27000, "L": 30000}, "custom": True},
            "hot_choco":   {"name": "Горячий шоколад",   "sizes": {"M": 30000, "L": 33000}, "custom": True},
            "espresso":    {"name": "Эспрессо",          "sizes": {"-": 15000},             "custom": False},
            "espresso2":   {"name": "Эспрессо двойной",  "sizes": {"-": 20000},             "custom": False},
        },
    },
    "cold": {
        "title": "🧊 Холодный кофе",
        "drinks": {
            "ice_americano":  {"name": "Айс Американо",        "sizes": {"M": 22000, "L": 25000}, "custom": True},
            "ice_cappuccino": {"name": "Айс Капучино",         "sizes": {"M": 25000, "L": 27000}, "custom": True},
            "ice_latte":      {"name": "Айс Латте",            "sizes": {"M": 27000, "L": 30000}, "custom": True},
            "ice_raf":        {"name": "Айс Раф",              "sizes": {"M": 28000, "L": 32000}, "custom": True},
            "ice_raf_cream":  {"name": "Айс Раф на сливках",   "sizes": {"M": 37000, "L": 55000}, "custom": True},
            "ice_bek_mokko":  {"name": "Айс Бек мокко",        "sizes": {"M": 32000, "L": 35000}, "custom": True},
            "frappe":         {"name": "Фраппе (ассорти)",     "sizes": {"M": 35000, "L": 38000}, "custom": False},
            "milkshake":      {"name": "Банановый милкшейк",   "sizes": {"M": 30000, "L": 35000}, "custom": False},
            "bumble":         {"name": "Бамбл",                "sizes": {"M": 28000, "L": 33000}, "custom": False},
        },
    },
    "lemonade": {
        "title": "🍋 Лимонады и напитки",
        "drinks": {
            "lemon_nosugar": {"name": "Лимонад без сахара",  "sizes": {"M": 28000, "L": 30000}, "custom": False},
            "mango":         {"name": "Манго-маракуйя",      "sizes": {"M": 27000, "L": 30000}, "custom": False},
            "tarhun":        {"name": "Тархун",              "sizes": {"M": 27000, "L": 30000}, "custom": False},
            "ice_tea":       {"name": "Айс Ти",              "sizes": {"M": 25000, "L": 27000}, "custom": False},
            "bubble_tea":    {"name": "Бабл Ти (ассорти)",   "sizes": {"M": 40000, "L": 50000}, "custom": False},
        },
    },
}

SYRUPS = {
    "caramel":  "Карамель",
    "salted":   "Солёная карамель",
    "vanilla":  "Ваниль",
    "hazelnut": "Лесной орех",
    "coconut":  "Кокос",
}

# ─────────────────────────────────────────────────────────────
# i18n — короткий словарь интерфейса (ru / uz)
# ─────────────────────────────────────────────────────────────
TEXTS = {
    "ru": {
        "choose_lang": "Выберите язык / Tilni tanlang",
        "lang_set": "✅ Язык выбран: Русский",
        "welcome_new": "👋 Добро пожаловать в нашу кофейню!\n🎁 На ПЕРВЫЙ заказ — скидка 20%.",
        "menu_title": "Главное меню",
        "b_order": "☕ Заказать кофе",
        "b_repeat": "🔁 Мой обычный (повторить)",
        "b_purchases": "📦 Мои покупки",
        "b_free": "🎁 Бесплатная чашка",
        "b_status": "🏆 Мой статус",
        "b_history": "📜 История",
        "b_qr": "📱 Мой QR-код",
        "b_lang": "⚙️ Сменить язык",
        "choose_cat": "📋 Выберите категорию:",
        "choose_drink": "Выберите напиток:",
        "choose_size": "Выберите размер:",
        "choose_milk": "🥛 Выберите молоко:",
        "milk_normal": "🥛 Обычное молоко",
        "milk_lactose": f"🥥 Безлактозное (+{fmt(LACTOSE_FREE_PRICE)})",
        "choose_sweet": "🍯 Выберите подсластитель:",
        "s_none": "🚫 Без сахара",
        "s_sugar": "🍬 Сахар",
        "s_sweetener": "💊 Заменитель сахара",
        "s_syrup": "🍮 Сироп",
        "sugar_level": "🍬 Уровень сахара:",
        "sg_low": "▪️ Минимум",
        "sg_med": "▪️ Средний",
        "sg_high": "▪️ Сладкий",
        "tablets": "💊 Сколько таблеток?",
        "choose_syrup": "🍮 Выберите сироп:",
        "summary_title": "☕ Ваш заказ",
        "l_drink": "Напиток",
        "l_size": "Размер",
        "l_milk": "Молоко",
        "l_sweet": "Добавка",
        "l_syrup": "Сироп",
        "l_total": "Итого",
        "confirm": "✅ Подтвердить заказ",
        "cancel": "❌ Отмена",
        "no_syrup": "Без сиропа",
        "cancelled": "❌ Заказ отменён.",
        "accepted": "✅ Заказ принят!",
        "status_new": "Новый",
        "first_discount": "🎁 Скидка первого заказа −20%",
        "no_last_order": "У тебя ещё нет заказов — собери первый 🙂",
        "progress": "Прогресс лояльности",
        "left_to_free": "осталось {n} до бесплатной",
        "free_ready": "🎁 У тебя есть БЕСПЛАТНАЯ чашка! Скажи бариста.",
        "free_earned": "🎉 Поздравляем! Ты накопил {n} чашек — следующая БЕСПЛАТНО! 🎁",
        "free_used": "☕ Бесплатная чашка использована! Прогресс обнулён.",
        "free_none": "Бесплатной чашки пока нет. Копи дальше ☕",
        "my_purch": "📦 Куплено чашек: {c}\nДо бесплатной осталось: {l}",
        "status": "🏆 Мой статус\n\n⭐ Уровень: {lvl}\n☕ Всего заказов: {tot}\n📈 Прогресс: {c}/{m}\n🎁 Бесплатная: {free}",
        "yes": "Да", "no": "Нет",
        "hist_empty": "📜 История пока пуста.",
        "hist_title": "📜 Последние заказы:",
        "push_free": "🎁 Привет! Твоя бесплатная чашка кофе всё ещё ждёт ☕ Заходи!",
        "push_miss": "👋 Давно не виделись! ☕ {n}/{m} до бесплатной чашки. Ждём тебя!",
    },
    "uz": {
        "choose_lang": "Выберите язык / Tilni tanlang",
        "lang_set": "✅ Til tanlandi: O'zbekcha",
        "welcome_new": "👋 Qahvaxonamizga xush kelibsiz!\n🎁 BIRINCHI buyurtmaga — 20% chegirma.",
        "menu_title": "Asosiy menyu",
        "b_order": "☕ Qahva buyurtma qilish",
        "b_repeat": "🔁 Odatdagidek (takrorlash)",
        "b_purchases": "📦 Xaridlarim",
        "b_free": "🎁 Bepul chashka",
        "b_status": "🏆 Mening holatim",
        "b_history": "📜 Tarix",
        "b_qr": "📱 QR kodim",
        "b_lang": "⚙️ Tilni almashtirish",
        "choose_cat": "📋 Toifani tanlang:",
        "choose_drink": "Ichimlikni tanlang:",
        "choose_size": "Hajmni tanlang:",
        "choose_milk": "🥛 Sutni tanlang:",
        "milk_normal": "🥛 Oddiy sut",
        "milk_lactose": f"🥥 Laktozasiz (+{fmt(LACTOSE_FREE_PRICE)})",
        "choose_sweet": "🍯 Shirinlovchini tanlang:",
        "s_none": "🚫 Shakarsiz",
        "s_sugar": "🍬 Shakar",
        "s_sweetener": "💊 Shakar o‘rnini bosuvchi",
        "s_syrup": "🍮 Sirop",
        "sugar_level": "🍬 Shakar darajasi:",
        "sg_low": "▪️ Kam",
        "sg_med": "▪️ O‘rta",
        "sg_high": "▪️ Shirin",
        "tablets": "💊 Nechta tabletka?",
        "choose_syrup": "🍮 Siropni tanlang:",
        "summary_title": "☕ Sizning buyurtmangiz",
        "l_drink": "Ichimlik",
        "l_size": "Hajm",
        "l_milk": "Sut",
        "l_sweet": "Qo‘shimcha",
        "l_syrup": "Sirop",
        "l_total": "Jami",
        "confirm": "✅ Tasdiqlash",
        "cancel": "❌ Bekor qilish",
        "no_syrup": "Siropsiz",
        "cancelled": "❌ Buyurtma bekor qilindi.",
        "accepted": "✅ Buyurtma qabul qilindi!",
        "status_new": "Yangi",
        "first_discount": "🎁 Birinchi buyurtma chegirmasi −20%",
        "no_last_order": "Sizda hali buyurtma yo‘q — birinchisini tanlang 🙂",
        "progress": "Sodiqlik progressi",
        "left_to_free": "bepulgacha {n} qoldi",
        "free_ready": "🎁 Sizda BEPUL chashka bor! Baristaga ayting.",
        "free_earned": "🎉 Tabriklaymiz! {n} ta chashka yig‘dingiz — keyingisi BEPUL! 🎁",
        "free_used": "☕ Bepul chashka ishlatildi! Progress nollandi.",
        "free_none": "Hozircha bepul chashka yo‘q. Yig‘ishda davom eting ☕",
        "my_purch": "📦 Sotib olingan: {c}\nBepulgacha qoldi: {l}",
        "status": "🏆 Mening holatim\n\n⭐ Daraja: {lvl}\n☕ Jami buyurtma: {tot}\n📈 Progress: {c}/{m}\n🎁 Bepul: {free}",
        "yes": "Ha", "no": "Yo‘q",
        "hist_empty": "📜 Tarix hozircha bo‘sh.",
        "hist_title": "📜 So‘nggi buyurtmalar:",
        "push_free": "🎁 Salom! Bepul qahvangiz hali ham kutyapti ☕ Keling!",
        "push_miss": "👋 Ko‘rishmaganimizga ancha bo‘ldi! ☕ Bepulgacha {n}/{m}. Kutamiz!",
    },
}


def T(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"][key])


# ─────────────────────────────────────────────────────────────
# БАЗА ДАННЫХ
# ─────────────────────────────────────────────────────────────
# На Railway база лежит на постоянном диске (Volume), путь задаётся в DB_PATH.
# Локально по умолчанию — файл рядом со скриптом.
DB_PATH = os.getenv("DB_PATH", "coffeebot.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,
    language      TEXT,
    cups_count    INTEGER DEFAULT 0,
    free_cup      INTEGER DEFAULT 0,
    last_order_at TEXT,
    last_notified TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id   INTEGER,
    purchase_date TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    drink       TEXT,
    size        TEXT,
    milk        TEXT,
    sweet       TEXT,
    syrup       TEXT,
    price       INTEGER,
    status      TEXT,
    created_at  TEXT
)
""")
conn.commit()


def migrate():
    """Добавляем недостающие колонки в старую базу, чтобы ничего не падало."""
    def cols(table):
        return [r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()]

    for col, ddl in [
        ("syrup", "ALTER TABLE orders ADD COLUMN syrup TEXT"),
    ]:
        if col not in cols("orders"):
            cursor.execute(ddl)
    for col, ddl in [
        ("last_order_at", "ALTER TABLE users ADD COLUMN last_order_at TEXT"),
        ("last_notified", "ALTER TABLE users ADD COLUMN last_notified TEXT"),
    ]:
        if col not in cols("users"):
            cursor.execute(ddl)
    conn.commit()


migrate()


# ─────────────────────────────────────────────────────────────
# ХЕЛПЕРЫ БД
# ─────────────────────────────────────────────────────────────
def ensure_user(telegram_id, lang=None):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, language) VALUES (?, ?)",
        (telegram_id, lang or "ru"),
    )
    if lang:
        cursor.execute(
            "UPDATE users SET language = ? WHERE telegram_id = ?",
            (lang, telegram_id),
        )
    conn.commit()


def get_lang(context, telegram_id):
    lang = context.user_data.get("lang")
    if lang:
        return lang
    row = cursor.execute(
        "SELECT language FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    return row[0] if row and row[0] else "ru"


def order_count(telegram_id):
    return cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE telegram_id = ? AND status != 'cancel'",
        (telegram_id,),
    ).fetchone()[0]


def get_cups(telegram_id):
    row = cursor.execute(
        "SELECT cups_count, free_cup FROM users WHERE telegram_id = ?",
        (telegram_id,),
    ).fetchone()
    return (row[0], row[1]) if row else (0, 0)


def progress_line(lang, telegram_id):
    cups, free = get_cups(telegram_id)
    if free:
        return T(lang, "free_ready")
    filled = min(cups, CUPS_FOR_FREE)
    bar = "☕" * filled + "⚪" * (CUPS_FOR_FREE - filled)
    left = CUPS_FOR_FREE - cups
    return f"{bar}  ({T(lang, 'left_to_free').format(n=left)})"


def clear_order(context):
    for k in ("cat", "drink", "drink_key", "size", "milk", "sweet",
              "syrup", "base_price", "price", "custom"):
        context.user_data.pop(k, None)


# ─────────────────────────────────────────────────────────────
# /start  +  ВЫБОР ЯЗЫКА
# ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    is_new = cursor.execute(
        "SELECT 1 FROM users WHERE telegram_id = ?", (uid,)
    ).fetchone() is None
    ensure_user(uid)

    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="ru")],
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="uz")],
    ]
    if is_new:
        await update.message.reply_text(T("ru", "welcome_new"))
    await update.message.reply_text(
        TEXTS["ru"]["choose_lang"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data
    context.user_data["lang"] = lang
    ensure_user(query.from_user.id, lang)
    await query.edit_message_text(T(lang, "lang_set"))
    await show_main_menu(query.message, lang, query.from_user.id)


async def show_main_menu(message, lang, telegram_id):
    keyboard = [
        [InlineKeyboardButton(T(lang, "b_order"), callback_data="buy_coffee")],
        [InlineKeyboardButton(T(lang, "b_repeat"), callback_data="repeat")],
        [InlineKeyboardButton(T(lang, "b_purchases"), callback_data="my_purchases")],
        [InlineKeyboardButton(T(lang, "b_free"), callback_data="use_free_cup")],
        [InlineKeyboardButton(T(lang, "b_status"), callback_data="my_status")],
        [InlineKeyboardButton(T(lang, "b_history"), callback_data="history")],
        [InlineKeyboardButton(T(lang, "b_qr"), callback_data="my_qr")],
        [InlineKeyboardButton(T(lang, "b_lang"), callback_data="change_language")],
    ]
    await message.reply_text(
        f"{T(lang, 'menu_title')}\n\n{progress_line(lang, telegram_id)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ─────────────────────────────────────────────────────────────
# ЭКРАН ПОДТВЕРЖДЕНИЯ ЗАКАЗА
# ─────────────────────────────────────────────────────────────
async def show_order_summary(message, context, lang, telegram_id):
    d = context.user_data
    drink = d.get("drink", "-")
    size = d.get("size", "")
    milk = d.get("milk", "—")
    sweet = d.get("sweet", "—")
    syrup = d.get("syrup", T(lang, "no_syrup"))
    price = d.get("price", 0)

    is_first = order_count(telegram_id) == 0
    shown_price = int(price * (1 - FIRST_ORDER_DISCOUNT)) if is_first else price

    lines = [f"<b>{T(lang, 'summary_title')}</b>\n"]
    lines.append(f"{T(lang, 'l_drink')}: {drink} {size}".strip())
    if d.get("custom"):
        lines.append(f"{T(lang, 'l_milk')}: {milk}")
        lines.append(f"{T(lang, 'l_sweet')}: {sweet}")
        lines.append(f"{T(lang, 'l_syrup')}: {syrup}")
    if is_first:
        lines.append(f"\n<s>{fmt(price)}</s> → <b>{fmt(shown_price)}</b> сум")
        lines.append(T(lang, "first_discount"))
    else:
        lines.append(f"\n💰 {T(lang, 'l_total')}: <b>{fmt(shown_price)}</b> сум")

    keyboard = [
        [InlineKeyboardButton(T(lang, "confirm"), callback_data="confirm_order")],
        [InlineKeyboardButton(T(lang, "cancel"), callback_data="cancel_order")],
    ]
    await message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ─────────────────────────────────────────────────────────────
# ГЛАВНЫЙ ОБРАБОТЧИК КНОПОК
# ─────────────────────────────────────────────────────────────
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    lang = get_lang(context, uid)
    msg = query.message

    # ── Открыть категории ──
    if data in ("buy_coffee", "menu_coffee"):
        clear_order(context)
        keyboard = [
            [InlineKeyboardButton(MENU["hot"]["title"], callback_data="cat:hot")],
            [InlineKeyboardButton(MENU["cold"]["title"], callback_data="cat:cold")],
            [InlineKeyboardButton(MENU["lemonade"]["title"], callback_data="cat:lemonade")],
        ]
        await msg.reply_text(T(lang, "choose_cat"),
                             reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Список напитков категории ──
    elif data.startswith("cat:"):
        cat = data.split(":")[1]
        keyboard = [
            [InlineKeyboardButton(d["name"], callback_data=f"drink:{cat}:{key}")]
            for key, d in MENU[cat]["drinks"].items()
        ]
        await msg.reply_text(f"{MENU[cat]['title']}\n\n{T(lang, 'choose_drink')}",
                             reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Выбор размера ──
    elif data.startswith("drink:"):
        _, cat, key = data.split(":")
        drink = MENU[cat]["drinks"][key]
        context.user_data.update({"cat": cat, "drink_key": key,
                                  "drink": drink["name"], "custom": drink["custom"]})
        buttons = []
        for size, price in drink["sizes"].items():
            label = f"{fmt(price)} сум" if size == "-" else f"{size} — {fmt(price)}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"size:{cat}:{key}:{size}")])
        await msg.reply_text(f"{drink['name']}\n\n{T(lang, 'choose_size')}",
                             reply_markup=InlineKeyboardMarkup(buttons))

    # ── Размер выбран ──
    elif data.startswith("size:"):
        _, cat, key, size = data.split(":")
        drink = MENU[cat]["drinks"][key]
        price = drink["sizes"][size]
        context.user_data["size"] = "" if size == "-" else size
        context.user_data["base_price"] = price
        context.user_data["price"] = price
        if drink["custom"]:
            keyboard = [
                [InlineKeyboardButton(T(lang, "milk_normal"), callback_data="milk:normal")],
                [InlineKeyboardButton(T(lang, "milk_lactose"), callback_data="milk:lactose")],
            ]
            await msg.reply_text(T(lang, "choose_milk"),
                                 reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await show_order_summary(msg, context, lang, uid)

    # ── Молоко ──
    elif data.startswith("milk:"):
        kind = data.split(":")[1]
        if kind == "lactose":
            context.user_data["milk"] = "Безлактозное"
            context.user_data["price"] += LACTOSE_FREE_PRICE
        else:
            context.user_data["milk"] = "Обычное"
        keyboard = [
            [InlineKeyboardButton(T(lang, "s_none"), callback_data="sugar:none")],
            [InlineKeyboardButton(T(lang, "s_sugar"), callback_data="sugar:menu")],
            [InlineKeyboardButton(T(lang, "s_sweetener"), callback_data="sweet:menu")],
            [InlineKeyboardButton(T(lang, "s_syrup"), callback_data="syrup:menu")],
        ]
        await msg.reply_text(T(lang, "choose_sweet"),
                             reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Сахар ──
    elif data == "sugar:menu":
        keyboard = [
            [InlineKeyboardButton(T(lang, "sg_low"), callback_data="sugar:low")],
            [InlineKeyboardButton(T(lang, "sg_med"), callback_data="sugar:med")],
            [InlineKeyboardButton(T(lang, "sg_high"), callback_data="sugar:high")],
        ]
        await msg.reply_text(T(lang, "sugar_level"),
                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif data in ("sugar:none", "sugar:low", "sugar:med", "sugar:high"):
        mapping = {
            "sugar:none": "Без сахара", "sugar:low": "Мало сахара",
            "sugar:med": "Средний сахар", "sugar:high": "Много сахара",
        }
        context.user_data["sweet"] = mapping[data]
        await show_order_summary(msg, context, lang, uid)

    # ── Заменитель сахара ──
    elif data == "sweet:menu":
        keyboard = [
            [InlineKeyboardButton(f"{i} 💊", callback_data=f"sweet:{i}")]
            for i in (1, 2, 3, 4)
        ]
        await msg.reply_text(T(lang, "tablets"),
                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("sweet:") and data != "sweet:menu":
        n = data.split(":")[1]
        context.user_data["sweet"] = f"{n} табл. сахарозаменителя"
        await show_order_summary(msg, context, lang, uid)

    # ── Сироп ──
    elif data == "syrup:menu":
        keyboard = [
            [InlineKeyboardButton(f"{name} (+{fmt(SYRUP_PRICE)})", callback_data=f"syrup:{k}")]
            for k, name in SYRUPS.items()
        ]
        await msg.reply_text(T(lang, "choose_syrup"),
                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("syrup:") and data != "syrup:menu":
        k = data.split(":")[1]
        context.user_data["syrup"] = SYRUPS[k]
        context.user_data["price"] += SYRUP_PRICE
        context.user_data.setdefault("sweet", "Без сахара")
        await show_order_summary(msg, context, lang, uid)

    # ── Повтор последнего заказа ──
    elif data == "repeat":
        row = cursor.execute(
            """SELECT drink, size, milk, sweet, syrup, price
               FROM orders WHERE telegram_id = ? AND status != 'cancel'
               ORDER BY id DESC LIMIT 1""", (uid,)
        ).fetchone()
        if not row:
            await msg.reply_text(T(lang, "no_last_order"))
            return
        clear_order(context)
        context.user_data.update({
            "drink": row[0], "size": row[1], "milk": row[2],
            "sweet": row[3], "syrup": row[4], "price": row[5],
            "custom": bool(row[2]),  # было молоко -> кастомный
        })
        await show_order_summary(msg, context, lang, uid)

    # ── Подтверждение заказа ──
    elif data == "confirm_order":
        await confirm_order(query, context, lang, uid)

    elif data == "cancel_order":
        clear_order(context)
        await msg.reply_text(T(lang, "cancelled"))

    # ── Мои покупки ──
    elif data == "my_purchases":
        cups, _ = get_cups(uid)
        left = max(0, CUPS_FOR_FREE - cups)
        await msg.reply_text(T(lang, "my_purch").format(c=cups, l=left))

    # ── Статус ──
    elif data == "my_status":
        total = order_count(uid)
        cups, free = get_cups(uid)
        lvl = "🥇 Gold" if total >= 50 else "🥈 Silver" if total >= 10 else "🥉 Bronze"
        await msg.reply_text(T(lang, "status").format(
            lvl=lvl, tot=total, c=cups, m=CUPS_FOR_FREE,
            free=T(lang, "yes") if free else T(lang, "no")))

    # ── История ──
    elif data == "history":
        rows = cursor.execute(
            """SELECT created_at, drink, size, price FROM orders
               WHERE telegram_id = ? AND status != 'cancel'
               ORDER BY id DESC LIMIT 10""", (uid,)
        ).fetchall()
        if not rows:
            await msg.reply_text(T(lang, "hist_empty"))
        else:
            text = T(lang, "hist_title") + "\n\n"
            for i, r in enumerate(rows, 1):
                text += f"{i}. {r[1]} {r[2]} — {fmt(r[3])} сум\n   🕒 {r[0]}\n"
            await msg.reply_text(text)

    # ── QR ──
    elif data == "my_qr":
        await send_qr(msg, uid)

    # ── Сменить язык ──
    elif data == "change_language":
        keyboard = [[
            InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="uz"),
        ]]
        await msg.reply_text(TEXTS["ru"]["choose_lang"],
                             reply_markup=InlineKeyboardMarkup(keyboard))

    # ── Использовать бесплатную чашку ──
    elif data == "use_free_cup":
        _, free = get_cups(uid)
        if free:
            cursor.execute(
                "UPDATE users SET cups_count = 0, free_cup = 0 WHERE telegram_id = ?",
                (uid,))
            conn.commit()
            await msg.reply_text(T(lang, "free_used"))
        else:
            await msg.reply_text(T(lang, "free_none"))


async def confirm_order(query, context, lang, uid):
    d = context.user_data
    drink = d.get("drink", "")
    size = d.get("size", "")
    milk = d.get("milk", "—")
    sweet = d.get("sweet", "—")
    syrup = d.get("syrup", T(lang, "no_syrup"))
    price = d.get("price", 0)

    ensure_user(uid, lang)
    is_first = order_count(uid) == 0
    final_price = int(price * (1 - FIRST_ORDER_DISCOUNT)) if is_first else price

    # сохраняем заказ
    cursor.execute(
        """INSERT INTO orders
           (telegram_id, drink, size, milk, sweet, syrup, price, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'new', datetime('now', ?))""",
        (uid, drink, size, milk, sweet, syrup, final_price, TZ),
    )
    order_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO purchases (telegram_id, purchase_date) VALUES (?, datetime('now', ?))",
        (uid, TZ),
    )

    # ── авто-лояльность 7+1 ──
    cups, _ = get_cups(uid)
    cups += 1
    free = 1 if cups >= CUPS_FOR_FREE else 0
    cursor.execute(
        """UPDATE users SET cups_count = ?, free_cup = ?, last_order_at = datetime('now', ?)
           WHERE telegram_id = ?""",
        (cups, free, TZ, uid),
    )
    conn.commit()

    # уведомление админу
    disc = f"  ({T(lang, 'first_discount')})" if is_first else ""
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"🆕 Новый заказ #{order_id}\n\n"
                  f"☕ {drink} {size}\n🥛 {milk}\n🍬 {sweet}\n🍮 {syrup}\n"
                  f"💰 {fmt(final_price)} сум{disc}"),
        )
    except Exception as e:
        print("ADMIN NOTIFY ERROR:", e)

    # чек клиенту
    await query.message.reply_text(
        f"<b>🧾 ЧЕК #{order_id}</b>\n\n"
        f"☕ {drink} {size}\n🥛 {milk}\n🍬 {sweet}\n🍮 {syrup}\n"
        "──────────────\n"
        f"💰 <b>{fmt(final_price)} сум</b>\n"
        f"📋 {T(lang, 'status_new')}",
        parse_mode="HTML",
    )

    # достиг бесплатной?
    if free:
        await query.message.reply_text(T(lang, "free_earned").format(n=CUPS_FOR_FREE))
    else:
        await query.message.reply_text(progress_line(lang, uid))

    clear_order(context)


# ─────────────────────────────────────────────────────────────
# QR
# ─────────────────────────────────────────────────────────────
async def send_qr(message, telegram_id):
    img = qrcode.make(str(telegram_id))
    filename = f"qr_{telegram_id}.png"
    img.save(filename)
    try:
        with open(filename, "rb") as photo:
            await message.reply_photo(photo=photo,
                                      caption=f"📱 Ваш QR-код\nID: {telegram_id}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)


async def my_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_qr(update.message, update.effective_user.id)


# ─────────────────────────────────────────────────────────────
# АДМИН
# ─────────────────────────────────────────────────────────────
def is_admin(update):
    return update.effective_user.id == ADMIN_ID


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    purchases_count = cursor.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    free_cups = cursor.execute("SELECT COUNT(*) FROM users WHERE free_cup = 1").fetchone()[0]
    new_orders = cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'new'").fetchone()[0]
    today_orders = cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now', ?)", (TZ,)
    ).fetchone()[0]
    today_revenue = cursor.execute(
        "SELECT COALESCE(SUM(price),0) FROM orders WHERE status != 'cancel' AND date(created_at) = date('now', ?)",
        (TZ,),
    ).fetchone()[0]
    row = cursor.execute(
        """SELECT drink, COUNT(*) c FROM orders
           WHERE date(created_at) = date('now', ?) GROUP BY drink ORDER BY c DESC LIMIT 1""",
        (TZ,),
    ).fetchone()
    popular = row[0] if row else "Нет заказов"

    await update.message.reply_text(
        f"📊 Админ-панель\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"☕ Покупок всего: {purchases_count}\n"
        f"🎁 Активных бесплатных чашек: {free_cups}\n"
        f"🆕 Новых заказов: {new_orders}\n\n"
        f"📅 Заказов сегодня: {today_orders}\n"
        f"💰 Выручка сегодня: {fmt(today_revenue)} сум\n"
        f"🏆 Популярный напиток: {popular}"
    )


async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    rows = cursor.execute(
        """SELECT id, drink, size, milk, sweet, syrup, price, status
           FROM orders ORDER BY id DESC LIMIT 5"""
    ).fetchall()
    labels = {"new": "🆕 Новый", "done": "✅ Готов", "cancel": "❌ Отменён"}
    text = "🧾 Последние заказы:\n\n"
    for r in rows:
        text += (f"#{r[0]}  {labels.get(r[7], r[7])}\n"
                 f"☕ {r[1]} {r[2]}\n🥛 {r[3]}\n🍬 {r[4]}\n🍮 {r[5]}\n"
                 f"💰 {fmt(r[6])} сум\n──────────────\n")
    await update.message.reply_text(text or "Заказов нет")


async def orders_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    rows = cursor.execute(
        """SELECT id, drink, size, milk, sweet, syrup, price, created_at
           FROM orders WHERE status = 'new' ORDER BY id DESC LIMIT 10"""
    ).fetchall()
    if not rows:
        await update.message.reply_text("✅ Новых заказов нет")
        return
    for r in rows:
        text = (f"#{r[0]}\n🕒 {r[7]}\n☕ {r[1]} {r[2]}\n"
                f"🥛 {r[3]}\n🍬 {r[4]}\n🍮 {r[5]}\n💰 {fmt(r[6])} сум")
        keyboard = [[
            InlineKeyboardButton("✅ Готов", callback_data=f"done_{r[0]}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{r[0]}"),
        ]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def order_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    if query.data.startswith("done_"):
        order_id = int(query.data.replace("done_", ""))
        cursor.execute("UPDATE orders SET status='done' WHERE id=?", (order_id,))
        conn.commit()
        uid = cursor.execute("SELECT telegram_id FROM orders WHERE id=?", (order_id,)).fetchone()[0]
        try:
            await context.bot.send_message(uid, "☕ Ваш заказ готов!\n\nПодойдите к стойке выдачи.")
        except Exception as e:
            print("NOTIFY ERROR:", e)
        await query.edit_message_text(f"✅ Заказ #{order_id} готов")
    elif query.data.startswith("cancel_"):
        order_id = int(query.data.replace("cancel_", ""))
        cursor.execute("UPDATE orders SET status='cancel' WHERE id=?", (order_id,))
        conn.commit()
        uid = cursor.execute("SELECT telegram_id FROM orders WHERE id=?", (order_id,)).fetchone()[0]
        try:
            await context.bot.send_message(uid, "❌ Ваш заказ отменён.\n\nОбратитесь к сотруднику кофейни.")
        except Exception as e:
            print("NOTIFY ERROR:", e)
        await query.edit_message_text(f"❌ Заказ #{order_id} отменён")


async def done_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование:\n/done НОМЕР_ЗАКАЗА")
        return
    order_id = int(context.args[0])
    cursor.execute("UPDATE orders SET status='done' WHERE id=?", (order_id,))
    conn.commit()
    await update.message.reply_text(f"✅ Заказ #{order_id} отмечен как готовый")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование:\n/cancel НОМЕР_ЗАКАЗА")
        return
    order_id = int(context.args[0])
    cursor.execute("UPDATE orders SET status='cancel' WHERE id=?", (order_id,))
    conn.commit()
    await update.message.reply_text(f"❌ Заказ #{order_id} отменён")


async def addcup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование:\n/addcup TELEGRAM_ID")
        return
    telegram_id = int(context.args[0])
    row = cursor.execute("SELECT cups_count FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if not row:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    cups = row[0] + 1
    free = 1 if cups >= CUPS_FOR_FREE else 0
    cursor.execute("UPDATE users SET cups_count=?, free_cup=? WHERE telegram_id=?",
                   (cups, free, telegram_id))
    conn.commit()
    await update.message.reply_text(f"✅ Чашка начислена\nID: {telegram_id}\nВсего чашек: {cups}")


# ─────────────────────────────────────────────────────────────
# ВОЗВРАТ СПЯЩИХ (фоновая задача JobQueue)
# ─────────────────────────────────────────────────────────────
async def check_inactive(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot

    # 1) у кого есть неиспользованная бесплатная чашка (раз в 3 дня)
    rows = cursor.execute(
        f"""SELECT telegram_id, language FROM users
            WHERE free_cup = 1
            AND (last_notified IS NULL OR last_notified < datetime('now', ?, '-3 days'))""",
        (TZ,),
    ).fetchall()
    for uid, lang in rows:
        lang = lang or "ru"
        try:
            await bot.send_message(uid, T(lang, "push_free"))
            cursor.execute("UPDATE users SET last_notified = datetime('now', ?) WHERE telegram_id = ?", (TZ, uid))
            conn.commit()
        except Exception as e:
            print("PUSH(free) ERROR:", uid, e)

    # 2) кто не заказывал > INACTIVE_DAYS дней (не чаще раза в INACTIVE_DAYS)
    rows = cursor.execute(
        f"""SELECT telegram_id, language, cups_count FROM users
            WHERE last_order_at IS NOT NULL
            AND last_order_at < datetime('now', ?, '-{INACTIVE_DAYS} days')
            AND free_cup = 0
            AND (last_notified IS NULL OR last_notified < datetime('now', ?, '-{INACTIVE_DAYS} days'))""",
        (TZ, TZ),
    ).fetchall()
    for uid, lang, cups in rows:
        lang = lang or "ru"
        try:
            await bot.send_message(uid, T(lang, "push_miss").format(n=cups, m=CUPS_FOR_FREE))
            cursor.execute("UPDATE users SET last_notified = datetime('now', ?) WHERE telegram_id = ?", (TZ, uid))
            conn.commit()
        except Exception as e:
            print("PUSH(miss) ERROR:", uid, e)


# ─────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    # команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myqr", my_qr))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("orders_new", orders_new))
    app.add_handler(CommandHandler("done", done_order))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("addcup", addcup))

    # колбэки (порядок важен!)
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^(ru|uz)$"))
    app.add_handler(CallbackQueryHandler(order_buttons, pattern="^(done_|cancel_)"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    # фоновая рассылка раз в сутки (нужен пакет с job-queue)
    if app.job_queue:
        app.job_queue.run_repeating(check_inactive, interval=86400, first=60)
    else:
        print("⚠️  JobQueue не установлен — пуши отключены. "
              "Установи: pip install \"python-telegram-bot[job-queue]\"")

    print("CoffeeBot v2 запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
