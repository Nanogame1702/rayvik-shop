# 🎮 RAYVIK SHOP - Free Fire Telegram Bot

Telegram бот-магазин для продажи модов и алмазов Free Fire с интеграцией Mini App.

## 🚀 Возможности

- 💎 Продажа алмазов Free Fire
- 🔥 Приватные моды и читы
- 🎁 Система промокодов
- 📊 Админ-панель
- 📣 Система рассылок (обычные, отложенные, повторяющиеся)
- 💳 Приём платежей (Карта, ЮMoney, СБП)
- 🌐 Mini App (веб-приложение внутри Telegram)

## 📦 Установка

1. Клонируй репозиторий:
```bash
git clone <твой-репозиторий>
cd shop
```

2. Создай виртуальное окружение:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. Установи зависимости:
```bash
pip install -r requirements.txt
```

4. Настрой переменные окружения:
```bash
copy .env.example .env
# Отредактируй .env и добавь свои данные
```

5. Запусти бота:
```bash
python bot.py
```

## ⚙️ Настройка Mini App

1. Загрузи папку `webapp_deploy` на Vercel или GitHub Pages
2. Получи URL (например: `https://твой-проект.vercel.app`)
3. Обнови `WEBAPP_URL` в `handlers/start.py`
4. Перезапусти бота

## 🔧 Команды администратора

- `/stats` - Статистика бота
- `/broadcast` - Рассылка всем пользователям
- `/buyers_broadcast` - Рассылка только покупателям
- `/dm <user_id> <текст>` - Отправить сообщение пользователю
- `/dm_multi <id1,id2> <текст>` - Отправить нескольким
- `/refund <order_id>` - Оформить возврат
- `/addpromo` - Создать промокод
- `/promos` - Список промокодов
- `/delpromo <код>` - Удалить промокод
- `/togglepromo <код>` - Включить/выключить промокод

## 📁 Структура проекта

```
shop/
├── bot.py              # Главный файл запуска
├── config.py           # Конфигурация
├── database.py         # База данных
├── keyboards.py        # Клавиатуры
├── handlers/           # Обработчики команд
├── services/           # Сервисы
├── scheduler/          # Планировщик рассылок
├── utils/              # Утилиты
├── webapp_deploy/      # Mini App для Vercel
└── index.html          # Главная страница Mini App
```

## 🛡️ Безопасность

⚠️ **Важно:** Не коммить файл `.env` с реальными токенами и реквизитами!

## 📄 Лицензия

MIT
