import os
from dotenv import load_dotenv

load_dotenv()

# Определяем окружение (Railway автоматически устанавливает RAILWAY_ENVIRONMENT)
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
IS_PRODUCTION = IS_RAILWAY or os.getenv('ENVIRONMENT') == 'production'

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN', 'ВАШ_ТОКЕН_БОТА')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', 'ВАШ_TELEGRAM_ID').split(',')))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'chingiz2111')

# Настройки вебхука для Railway
if IS_PRODUCTION:
    # Railway автоматически предоставляет URL через RAILWAY_STATIC_URL
    RAILWAY_URL = os.getenv('RAILWAY_STATIC_URL')
    if RAILWAY_URL:
        WEBHOOK_URL = f"{RAILWAY_URL}/webhook"
    else:
        # Альтернативный способ получения URL на Railway
        service_name = os.getenv('RAILWAY_SERVICE_NAME', '')
        if service_name:
            WEBHOOK_URL = f"https://{service_name}.up.railway.app/webhook"
        else:
            WEBHOOK_URL = ''

    # Flask на Railway должен использовать стандартный PORT
    WEBAPP_HOST = '0.0.0.0'
    WEBAPP_PORT = int(os.getenv('PORT', 5000))  # Railway устанавливает PORT
    BOT_MODE = "webhook"
else:
    # Локальная разработка
    WEBHOOK_URL = ''
    WEBAPP_HOST = '0.0.0.0'
    WEBAPP_PORT = 3001
    BOT_MODE = "polling"

# Настройки партнёрской программы
REFERRAL_PERCENT = 10  # Стандартный процент
REFERRAL_PERCENT_PREMIUM = 20  # Премиум процент (3+ реферала)
MIN_REFERRALS_FOR_PREMIUM = 3
CURRENCY = '₸'  # Казахстанский тенге