# RAYVIK SHOP - Mini App

Веб-приложение для Telegram Mini App

## Как загрузить на Vercel:

1. Зайди на https://vercel.com
2. Нажми "Add New" → "Project"
3. Перетащи папку `webapp_deploy` или выбери через "Import"
4. Нажми "Deploy"
5. После деплоя скопируй URL (например: https://твой-проект.vercel.app)
6. Вставь этот URL в файл `handlers/start.py` в переменную `WEBAPP_URL`
7. Перезапусти бота

## Файлы:
- `index.html` - главная страница магазина
- `styles.css` - стили (если есть отдельно)
- `vercel.json` - конфигурация для Vercel
