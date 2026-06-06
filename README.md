# ☕ CoffeeBot — Telegram-бот кофейни

Бот приёма заказов + программа лояльности 7+1. Работает на Railway 24/7.

## 📦 Что внутри
- `bot.py` — код бота
- `requirements.txt` — зависимости
- `Procfile` — команда запуска (`worker: python bot.py`)
- `.gitignore` — что не загружать

## 🚀 Запуск на Railway (по шагам)

### 1. GitHub
1. Заведи аккаунт на https://github.com (если нет).
2. Создай новый репозиторий: **New repository** → имя `coffeebot` → Create.
3. На странице репозитория: **Add file → Upload files** → перетащи сюда
   все файлы из этой папки → **Commit changes**.

### 2. Railway
1. Зайди на https://railway.app, войди через **GitHub**.
2. **New Project → Deploy from GitHub repo** → выбери `coffeebot`.
3. Railway сам найдёт `requirements.txt` и `Procfile` и начнёт сборку.

### 3. Токен бота (ОБЯЗАТЕЛЬНО)
1. В проекте Railway открой вкладку **Variables**.
2. Добавь переменную:
   - `BOT_TOKEN` = токен от @BotFather (новый!)
3. Railway перезапустит бота с токеном.

### 4. Постоянная база данных (чтобы не терять клиентов)
1. В сервисе нажми **+ New → Volume** (или **Settings → Volumes**).
2. **Mount path:** `/data`
3. Во вкладке **Variables** добавь:
   - `DB_PATH` = `/data/coffeebot.db`

Готово — бот в облаке. Проверь: напиши боту `/start`.

## 🔐 Безопасность
- Токен хранится ТОЛЬКО в Variables на Railway, не в коде.
- Если токен где-то засветился — отзови его в @BotFather (Revoke) и впиши новый в Variables.

## ⚙️ Настройки внутри `bot.py`
- `ADMIN_ID` — Telegram ID администратора кофейни
- `CUPS_FOR_FREE` — чашек до бесплатной (по умолчанию 7)
- `FIRST_ORDER_DISCOUNT` — скидка первого заказа (0.20 = 20%)
- `INACTIVE_DAYS` — через сколько дней напоминать «спящим» (7)
