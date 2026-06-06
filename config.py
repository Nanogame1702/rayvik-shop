import os
from dotenv import load_dotenv

load_dotenv()

# ТОКЕН И ID из .env или напрямую (для локальной разработки)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8893140608:AAGwKK-RN8Lxse3ZZVDj1ycTJYjB7dr-yYQ')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7519276489'))

# Реквизиты
PAYMENT_CARD = os.getenv('PAYMENT_CARD', "2204120136037708")
PAYMENT_YOOMONEY = os.getenv('PAYMENT_YOOMONEY', "4100119468058450")
PAYMENT_SBP_PHONE = os.getenv('PAYMENT_SBP_PHONE', "+774702796924")
PAYMENT_SBP_NAME = os.getenv('PAYMENT_SBP_NAME', "Любовь Ивановна С.")
PAYMENT_SBP_BANK = os.getenv('PAYMENT_SBP_BANK', "ЮMoney")

# Эмодзи
EMOJI = {
    'fire': '🔥', 'star': '⭐', 'diamond': '💎', 'check': '✅',
    'cross': '❌', 'money': '💰', 'card': '💳', 'arrow': '➡️',
    'back': '◀️', 'cart': '🛒', 'package': '📦', 'heart': '🖤',
    'alert': '‼️', 'lock': '🔒', 'lightning': '⚡️', 'berry': '🍓',
    'plane': '✈️', 'purple': '💜', 'wind': '💨', 'clock': '⏱'
}

print(f"✓ Токен: {BOT_TOKEN[:10]}...")
print(f"✓ ADMIN_ID: {ADMIN_ID}")


# Safe defaults for missing emoji keys
EMOJI.setdefault('megaphone', '📣')
