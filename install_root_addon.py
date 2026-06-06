# -*- coding: utf-8 -*-
"""
Авто-установщик под структуру:
D:\pravki\
  bot.py
  config.py
  handlers/
  utils/
  services/
  scheduler/
"""
import re, shutil, sys
from pathlib import Path

PRINT = "[installer]"

ROOT = Path.cwd()          # ожидаем запуск из D:\pravki
BOT  = ROOT / "bot.py"
CFG  = ROOT / "config.py"

REQUIRED = [
    ROOT/"handlers"/"broadcast_plus.py",
    ROOT/"handlers"/"broadcast_scheduler.py",
    ROOT/"handlers"/"admin_tools.py",
    ROOT/"utils"/"broadcast_sender.py",
    ROOT/"services"/"scheduled_repo.py",
    ROOT/"scheduler"/"runner.py",
]

def fail(msg: str, code: int = 2):
    print(f"{PRINT} ❌ {msg}")
    sys.exit(code)

def info(msg: str):
    print(f"{PRINT} {msg}")

def ensure_files():
    miss = [str(p) for p in REQUIRED if not p.exists()]
    if miss:
        fail("Не найдены файлы аддона:\n  - " + "\n  - ".join(miss) +
             "\nСкопируй их из архива в соответствующие папки и повтори запуск.")
    info("✓ Все необходимые файлы на месте.")

def show_admin_id():
    if not CFG.exists():
        info("config.py не найден — пропускаю вывод ADMIN_ID.")
        return
    txt = CFG.read_text(encoding="utf-8")
    m = re.search(r"ADMIN_ID\s*=\s*([0-9]+)", txt)
    if m:
        info(f"ADMIN_ID в config.py: {m.group(1)}")
    else:
        info("ADMIN_ID в config.py не найден — проверь вручную.")

def patch_bot():
    if not BOT.exists():
        fail("Не найден bot.py в текущей папке. Запусти скрипт строго из корня проекта (где лежит bot.py).")

    src = BOT.read_text(encoding="utf-8")
    original = src

    imp_pat = r"from\s+handlers\s+import\s+([^\n]+)"
    m = re.search(imp_pat, src)
    needed = ["broadcast_plus", "broadcast_scheduler", "admin_tools"]

    if m:
        imports = [x.strip() for x in m.group(1).split(",")]
        changed = False
        for name in needed:
            if name not in imports:
                imports.append(name)
                changed = True
        if changed:
            new_line = "from handlers import " + ", ".join(imports)
            src = re.sub(imp_pat, new_line, src, count=1)
    else:
        src = "from handlers import broadcast_plus, broadcast_scheduler, admin_tools\n" + src

    include_block = (
        "    dp.include_router(broadcast_plus.router)\n"
        "    dp.include_router(broadcast_scheduler.router)\n"
        "    dp.include_router(admin_tools.router)\n"
    )
    if "dp.include_router(broadcast_plus.router)" not in src:
        m = re.search(r"dp\.include_router\(admin\.router\).*?\n", src)
        pos = m.end() if m else len(src)
        src = src[:pos] + include_block + src[pos:]

    if "start_runner(" not in src:
        src = re.sub(
            r"(\n\s*await\s+dp\.start_polling\(.*?\)\s*)",
            (
                "\n    # запуск фонового планировщика отложенных рассылок\n"
                "    try:\n"
                "        from scheduler.runner import start_runner\n"
                "        await start_runner(bot, admin_chat_id=ADMIN_ID if 'ADMIN_ID' in globals() else None)\n"
                "    except Exception:\n"
                "        logger.exception(\"Не удалось запустить планировщик отложенных рассылок\")\n"
                r"\1"
            ),
            src, flags=re.S
        )

    if src != original:
        backup = BOT.with_suffix(".py.bak")
        shutil.copy2(BOT, backup)
        BOT.write_text(src, encoding="utf-8")
        info(f"✓ bot.py пропатчен. Создан бэкап: {backup.name}")
    else:
        info("= bot.py уже был настроен — изменений не требуется.")

def main():
    info(f"Working dir: {ROOT}")
    ensure_files()
    patch_bot()
    show_admin_id()
    info("✅ Готово. Перезапусти бота и проверь /id, /is_admin, /broadcast_plus, /broadcast_at.")

if __name__ == "__main__":
    main()
