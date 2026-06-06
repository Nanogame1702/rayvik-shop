LUNO — добавление рассылок по времени и конструктор кнопок
=========================================================

Состав архива:
- lunost_shop_bo/lunost_shop_bo/handlers/broadcast_plus.py         — мгновенная рассылка с конструктором кнопок
- lunost_shop_bo/lunost_shop_bo/handlers/broadcast_scheduler.py    — мастер отложенной рассылки (по времени)
- lunost_shop_bo/lunost_shop_bo/utils/broadcast_sender.py          — единый отправщик (батчи/троттлинг/прогресс)
- lunost_shop_bo/lunost_shop_bo/services/scheduled_repo.py         — доступ к БД (таблица расписаний)
- lunost_shop_bo/lunost_shop_bo/scheduler/runner.py                — фоновый раннер, исполняет отложенные задачи
- migrations/001_add_scheduled_broadcasts.sql                      — миграция БД (таблица scheduled_broadcasts)
- patches/bot.patch                                                — unified diff для bot.py (минимальные вставки)
- scripts/test_repo.py                                             — мини-проверка репозитория расписаний

Требования:
- Python 3.10+ (желательно 3.11/3.12)
- Зависимости: aiogram (уже в проекте), aiosqlite, python-dotenv (есть), tzdata (Windows)

Быстрый запуск (чистая машина)
------------------------------
1) Установите зависимости (если нет файла requirements.txt — просто установите):

   pip install aiogram aiosqlite python-dotenv tzdata

2) Примените миграцию (создаст таблицу scheduled_broadcasts в shop_bot.db):

   cd lunost_shop_bo
   sqlite3 shop_bot.db < ../migrations/001_add_scheduled_broadcasts.sql

3) Подключите новые роутеры и планировщик в bot.py (примените патч):

   git apply patches/bot.patch     # если проект под git
   # или вручную внесите 3 вставки из patches/bot.patch

4) Запустите бота:

   python -m lunost_shop_bo.bot

Команды админа
--------------
- /broadcast_plus                 — мгновенная рассылка всем (с конструктором кнопок)
- /buyers_broadcast_plus          — мгновенная рассылка покупателям
- /broadcast_at                   — отложенная рассылка всем
- /buyers_broadcast_at            — отложенная рассылка покупателям
- /scheduled_broadcasts           — список активных/ожидающих задач

Формат времени
--------------
- Введите время как: YYYY-MM-DD HH:MM (по МСК). Пример: 2025-10-10 19:30
- В подтверждении бот покажет местное и UTC-время. В базе хранится UTC.

Чек-лист регрессии
------------------
- Старые команды /broadcast, /buyers_broadcast, /dm, /dm_multi — работают как прежде.
- Новые команды создают рассылку, кнопки кликабельны, предпросмотр есть.
- Время отложенной рассылки интерпретируется верно, сообщение уходит в нужную минуту.
- Перезапуск бота до наступления времени НЕ ломает задачу — она выполнится позже.

Откат
-----
- Удалите новые файлы (handlers/broadcast_*.py, utils/broadcast_sender.py, services/scheduled_repo.py, scheduler/runner.py)
- Откатите изменения bot.py (отмените патч).
- (Опционально) удалите таблицу scheduled_broadcasts из shop_bot.db.
