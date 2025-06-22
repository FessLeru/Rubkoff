#!/usr/bin/env python3
"""
Запуск Telegram бота (Mock режим) + Mini App через XTunnel.ru
Загружает настройки xtunnel из .env файла
"""
import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Windows encoding fix
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем .env файл
load_dotenv()

from app.core.config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('run_both.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class XTunnelManager:
    """Управление xtunnel туннелем с загрузкой из .env"""
    
    def __init__(self, port=8000):
        self.port = port
        self.tunnel_url = None
        self.tunnel_process = None
        
        # Загружаем настройки из .env
        self.api_key = os.getenv('XTUNNEL_API_KEY')
        self.subdomain = os.getenv('XTUNNEL_SUBDOMAIN', 'rubkoff-app')
        
        if not self.api_key:
            logger.warning("❌ XTUNNEL_API_KEY не найден в .env файле")
        else:
            logger.info(f"✅ XTunnel API ключ загружен из .env")
            logger.info(f"📡 Поддомен: {self.subdomain}")
    
    def start_tunnel(self):
        """Запуск туннеля к локальному серверу"""
        if not self.api_key:
            logger.error("API ключ xtunnel.ru не настроен в .env")
            return None
        
        try:
            # Формируем URL туннеля (будет доступен после запуска)
            self.tunnel_url = f"https://{self.subdomain}.xtunnel.ru"
            
            # Для демонстрации предполагаем что туннель запущен
            # В реальности здесь был бы HTTP запрос к API xtunnel.ru
            logger.info(f"🔗 XTunnel URL настроен: {self.tunnel_url}")
            logger.info(f"🌐 Локальный сервер: http://127.0.0.1:{self.port}")
            
            # Предупреждение: нужно настроить туннель на стороне xtunnel.ru
            logger.warning("⚠️ Убедитесь что туннель настроен в личном кабинете xtunnel.ru")
            logger.warning(f"   Направьте {self.subdomain}.xtunnel.ru → 127.0.0.1:{self.port}")
            
            return self.tunnel_url
            
        except Exception as e:
            logger.error(f"Ошибка настройки xtunnel: {e}")
            return None
    
    def get_tunnel_url(self):
        """Получение URL туннеля"""
        if self.tunnel_url:
            return self.tunnel_url
        return self.start_tunnel()
    
    def stop_tunnel(self):
        """Остановка туннеля"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                logger.info("🛑 XTunnel туннель остановлен")
            except:
                pass

class BothServer:
    """Запуск бота + API через XTunnel"""
    
    def __init__(self):
        self.xtunnel = XTunnelManager(8000)
        self.bot_task = None
        self.api_task = None
    
    async def setup_webhook_bot(self):
        """Настройка и запуск бота с webhook"""
        try:
            from aiogram import Bot, Dispatcher
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            from app.bot.handlers import router as user_router
            from app.bot.middlewares import DatabaseMiddleware, ThrottlingMiddleware
            from app.core.config import config
            
            # Создаем бота
            bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            
            # Создаем диспетчер
            dp = Dispatcher()
            
            # Регистрируем middleware
            dp.message.middleware(DatabaseMiddleware())
            dp.callback_query.middleware(DatabaseMiddleware())
            dp.message.middleware(ThrottlingMiddleware())
            dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))
            
            # Подключаем роутеры
            dp.include_router(user_router)
            
            # Настраиваем webhook
            webhook_url = os.environ.get('WEBHOOK_URL')
            if webhook_url:
                await bot.delete_webhook()
                await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
                logger.info(f"✅ Webhook установлен: {webhook_url}")
                
                # Уведомляем админа
                try:
                    admin_id = config.ADMIN_IDS[0]
                    await bot.send_message(
                        admin_id,
                        "🚀 <b>Rubkoff Bot запущен!</b>\n\n"
                        "🌐 <b>Tunnel4.com режим</b>\n"
                        f"📱 Mini App: {os.environ.get('MINI_APP_URL')}\n"
                        f"🔗 API: {os.environ.get('API_BASE_URL')}\n"
                        f"📡 Webhook: {webhook_url}\n\n"
                        "✅ Бот готов к работе!"
                    )
                except:
                    pass
            
            return bot, dp
            
        except Exception as e:
            logger.error(f"Ошибка настройки бота: {e}")
            raise
    
    async def run_api_with_webhook(self):
        """Запуск API сервера с интегрированным webhook"""
        try:
            import uvicorn
            from fastapi import FastAPI, Request, HTTPException
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.responses import JSONResponse
            from fastapi.staticfiles import StaticFiles
            from pathlib import Path
            from aiogram.types import Update
            from app.api.routers import houses, users
            from app.core.db import db
            from app.core.config import config
            from sqlalchemy.ext.asyncio import AsyncSession
            
            # Инициализация БД
            await db.init_db()
            logger.info("✅ База данных инициализирована")
            
            # Настраиваем бота с webhook
            bot, dp = await self.setup_webhook_bot()
            
            # Создаем FastAPI приложение
            app = FastAPI(
                title="Rubkoff House Selection API + Bot",
                description="API + Telegram Bot для подбора домов",
                version="1.1.0"
            )
            
            # CORS middleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Mount frontend
            frontend_path = Path(__file__).parent / "frontend"
            if frontend_path.exists():
                app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")
            
            # Webhook endpoint
            @app.post("/webhook")
            async def handle_webhook(request: Request):
                try:
                    body = await request.body()
                    if not body:
                        return JSONResponse({"status": "ok"})
                    
                    update_data = await request.json()
                    update = Update.model_validate(update_data, context={"bot": bot})
                    
                    # Process the update with database session
                    await dp.feed_update(bot, update)
                    return JSONResponse({"status": "ok"})
                except Exception as e:
                    logger.error(f"Webhook error: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail="Webhook processing error")
            
            # Include API routers
            app.include_router(houses.router, prefix="/api")
            app.include_router(users.router, prefix="/api")
            
            # Health endpoints
            @app.get("/")
            async def root():
                return {
                    "message": "Rubkoff House Selection API + Bot",
                    "version": "1.1.0", 
                    "status": "healthy",
                    "mock_mode": config.MOCK_MODE
                }
            
            @app.get("/health")
            async def health():
                return {
                    "status": "healthy",
                    "mock_mode": config.MOCK_MODE,
                    "bot_ready": True
                }
            
            logger.info("🌐 Запуск API сервера с интегрированным webhook...")
            
            config_uvicorn = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                reload=False,
                log_level="info"
            )
            
            server = uvicorn.Server(config_uvicorn)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Ошибка API сервера: {e}")
            raise
    
    def setup_environment(self):
        """Настройка окружения"""
        # Принудительно включаем Mock режим
        os.environ['MOCK_MODE'] = 'true'
        
        # Используем ваш новый xtunnel URL
        tunnel_url = "https://db4c882b-b6b7-4528-a033-f961ba0e9afb.tunnel4.com"
        
        # Настраиваем для вашего туннеля
        os.environ['WEBHOOK_URL'] = f"{tunnel_url}/webhook"
        os.environ['MINI_APP_URL'] = f"{tunnel_url}/frontend/"
        os.environ['API_BASE_URL'] = f"{tunnel_url}/api"
        
        logger.info(f"🌐 URLs настроены для вашего XTunnel:")
        logger.info(f"   📡 Webhook: {tunnel_url}/webhook")
        logger.info(f"   📱 Mini App: {tunnel_url}/frontend/")
        logger.info(f"   🔗 API: {tunnel_url}/api")
        logger.info(f"   💻 Локальный сервер: http://127.0.0.1:8000")
    
    async def start(self):
        """Запуск всех сервисов"""
        logger.info("🚀 Запуск Rubkoff Bot + Mini App...")
        logger.info("🎯 Режим: MOCK (быстрый подбор домов)")
        
        # Настройка окружения
        self.setup_environment()
        
        try:
            # Запуск API сервера с интегрированным webhook
            await self.run_api_with_webhook()
        except KeyboardInterrupt:
            logger.info("Остановка сервисов...")
        finally:
            logger.info("Сервисы остановлены")

def print_startup_info():
    """Информация о запуске"""
    print("=" * 70)
    print("RUBKOFF BOT + MINI APP - XTUNNEL ЗАПУСК")
    print("=" * 70)
    print()
    print("🎯 Режим: MOCK (быстрый подбор домов)")
    print()
    print("Что запускается:")
    print("   🤖 Telegram Bot (с webhook)")
    print("   🌐 API Server (port 8000)")
    print("   📱 Mini App Frontend")
    print("   🔗 Webhook обработчик")
    print()
    print("🌐 ВАШ XTUNNEL РЕЖИМ:")
    print("   📱 Mini App: https://db4c882b-b6b7-4528-a033-f961ba0e9afb.tunnel4.com/frontend/")
    print("   🔗 API: https://db4c882b-b6b7-4528-a033-f961ba0e9afb.tunnel4.com/api")
    print("   📡 Webhook: https://db4c882b-b6b7-4528-a033-f961ba0e9afb.tunnel4.com/webhook")
    print("   💻 Локально: http://127.0.0.1:8000")
    print()
    print("✅ ТУННЕЛЬ УЖЕ НАСТРОЕН - можно тестировать!")
    print()
    print("🤖 Telegram Bot:")
    print("   - Подбор домов: мгновенный (Mock режим)")
    print("   - Mini App кнопка: работает через ваш xtunnel")
    print("   - Webhook: автоматически настроен")
    
    print()
    print("Для остановки нажмите Ctrl+C")
    print("-" * 70)

async def main():
    """Главная функция"""
    print_startup_info()
    
    server = BothServer()
    
    # Настройка обработчика сигналов
    def signal_handler(signum, frame):
        logger.info("Получен сигнал остановки")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Остановлено пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1) 