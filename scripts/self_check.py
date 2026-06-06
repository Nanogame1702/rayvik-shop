import importlib.util, sys, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
pkg = ROOT / "lunost_shop_bo"
print("Project root:", ROOT)
print("Has 'lunost_shop_bo' dir:", pkg.exists())

expected = [
    pkg / "handlers" / "broadcast_plus.py",
    pkg / "handlers" / "broadcast_scheduler.py",
    pkg / "handlers" / "admin_tools.py",
    pkg / "utils" / "broadcast_sender.py",
    pkg / "services" / "scheduled_repo.py",
    pkg / "scheduler" / "runner.py",
]
missing = [str(p) for p in expected if not p.exists()]
if missing:
    print("❌ Missing files:", *missing, sep="\n - ")
    sys.exit(1)

print("✅ Files are in place.")
print("Now check imports from bot.py:")
bot_path = pkg / "bot.py"
if not bot_path.exists():
    print("⚠️ bot.py not found at", bot_path)
else:
    src = bot_path.read_text(encoding="utf-8", errors="ignore")
    ok1 = "broadcast_plus" in src
    ok2 = "broadcast_scheduler" in src
    ok3 = "admin_tools" in src
    print(" - broadcast_plus import/usage:", "OK" if ok1 else "NO")
    print(" - broadcast_scheduler import/usage:", "OK" if ok2 else "NO")
    print(" - admin_tools import/usage:", "OK" if ok3 else "NO")
    if not (ok1 and ok2 and ok3):
        print("→ Добавьте импорты и dp.include_router(...) согласно инструкции.")
        sys.exit(2)
    print("✅ bot.py appears patched.")
