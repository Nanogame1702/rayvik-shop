import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from handlers import (
    start,
    catalog,
    payment,
    admin,
    promo,
    webapp,
    broadcast_plus,
    broadcast_scheduler,
    admin_tools,
    scheduled_manage,
    help,
    recurring_broadcast,
    recurring_manage
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Простой веб-сервер для Render (чтобы не засыпал)
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("Web server started on port 8080")

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных инициализирована")
    
    # Применяем миграции
    logger.info("Применение миграций...")
    try:
        from pathlib import Path
        import sqlite3
        migrations_dir = Path("migrations")
        if migrations_dir.exists():
            sql_files = sorted(migrations_dir.glob("*.sql"))
            with sqlite3.connect('shop_bot.db') as conn:
                for sql_file in sql_files:
                    try:
                        sql = sql_file.read_text(encoding="utf-8")
                        conn.executescript(sql)
                        conn.commit()
                        logger.info(f"✅ Миграция {sql_file.name} применена")
                    except Exception as e:
                        logger.warning(f"⚠️ Миграция {sql_file.name}: {e}")
    except Exception as e:
        logger.error(f"Ошибка применения миграций: {e}")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(broadcast_plus.router)
    dp.include_router(broadcast_scheduler.router)
    dp.include_router(recurring_broadcast.router)
    dp.include_router(recurring_manage.router)
    dp.include_router(admin_tools.router)
    dp.include_router(webapp.router)
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(promo.router)
    dp.include_router(payment.router)
    dp.include_router(scheduled_manage.router)
    dp.include_router(help.router)

    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")

    # запуск фонового планировщика отложенных рассылок
    try:
        from scheduler.runner import start_runner
        await start_runner(bot, admin_chat_id=ADMIN_ID)
        logger.info("Планировщик отложенных рассылок запущен успешно")
    except Exception:
        logger.exception("Не удалось запустить планировщик отложенных рассылок")

    # Запуск веб-сервера для Render
    await start_web_server()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception:
        logger.exception("Ошибка во время polling")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        logger.info("=" * 50)
        logger.info("RAYVIK SHOP BOT - Запуск")
        logger.info("=" * 50)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
