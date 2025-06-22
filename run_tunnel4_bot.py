#!/usr/bin/env python3
"""
Единый скрипт для запуска Rubkoff Bot + Mini App с tunnel4.com
Запускает и бота, и API сервер в одном процессе
"""
import os
import sys
import asyncio
import logging
from typing import Optional
import signal

# Устанавливаем переменные окружения для tunnel4.com
os.environ['MINI_APP_URL'] = 'https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/'
os.environ['API_BASE_URL'] = 'https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/api'
os.environ['WEBHOOK_URL'] = 'https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/webhook'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RubkoffLauncher:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.api_server = None
        self.running = False
        
    async def setup_bot(self):
        """Настройка Telegram бота"""
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from app.bot.handlers.user import user_router
        from app.bot.middlewares.throttling import ThrottlingMiddleware
        from app.services.house_selection import get_house_selection_service
        
        # Создаем бота
        self.bot = Bot(
            token=os.environ['BOT_TOKEN'],
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Создаем диспетчер
        self.dp = Dispatcher()
        
        # Подключаем middleware
        self.dp.message.middleware(ThrottlingMiddleware())
        
        # Подключаем роутеры
        self.dp.include_router(user_router)
        
        # Инициализируем сервис
        service = get_house_selection_service()
        await service.initialize()
        
        logger.info("🤖 Bot setup completed")
        
    async def setup_webhook(self):
        """Настройка webhook"""
        webhook_url = os.environ['WEBHOOK_URL']
        
        try:
            # Удаляем старый webhook
            await self.bot.delete_webhook()
            
            # Устанавливаем новый webhook
            await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )
            
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            
            # Отправляем уведомление админу
            try:
                admin_ids = os.environ.get('ADMIN_IDS', '').split(',')
                if admin_ids and admin_ids[0]:
                    await self.bot.send_message(
                        int(admin_ids[0]), 
                        "🚀 <b>Rubkoff Bot запущен!</b>\n\n"
                        "🌐 <b>Tunnel4.com режим</b>\n"
                        f"📱 Mini App: {os.environ['MINI_APP_URL']}frontend/\n"
                        f"🔗 API: {os.environ['API_BASE_URL']}\n"
                        f"📡 Webhook: {webhook_url}\n\n"
                        "✅ Бот готов к работе!"
                    )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка настройки webhook: {e}")
            raise
    
    async def start_api_server(self):
        """Запуск API сервера"""
        import uvicorn
        from app.api.main import app
        
        logger.info("🌐 Запуск API сервера...")
        
        # Конфигурация сервера
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True
        )
        
        self.api_server = uvicorn.Server(config)
        
        # Запускаем сервер
        await self.api_server.serve()
    
    async def handle_webhook(self, request):
        """Обработка webhook запросов"""
        from aiogram.types import Update
        from fastapi import Request
        
        try:
            update_data = await request.json()
            update = Update.model_validate(update_data, context={"bot": self.bot})
            await self.dp.feed_update(self.bot, update)
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
    
    async def start(self):
        """Запуск всех сервисов"""
        self.running = True
        
        logger.info("============================================================")
        logger.info("RUBKOFF BOT + MINI APP - TUNNEL4.COM РЕЖИМ")
        logger.info("============================================================")
        logger.info("🎯 Режим: MOCK (быстрый подбор домов)")
        logger.info("Что запускается:")
        logger.info("   🤖 Telegram Bot")
        logger.info("   🌐 API Server (port 8000)")
        logger.info("   📱 Mini App Frontend")
        logger.info("   🔗 Webhook endpoints")
        logger.info("")
        logger.info("🌐 TUNNEL4.COM РЕЖИМ:")
        logger.info("   📱 Mini App: https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/frontend/")
        logger.info("   🔗 API: https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/api")
        logger.info("   📡 Webhook: https://bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com/webhook")
        logger.info("   💻 Локально: http://127.0.0.1:8000")
        logger.info("")
        logger.info("✅ ТУННЕЛЬ УЖЕ НАСТРОЕН:")
        logger.info("   bb6fffc5-afcb-4f58-a544-335a0276c44c.tunnel4.com → 127.0.0.1:8000")
        logger.info("")
        logger.info("Для остановки нажмите Ctrl+C")
        logger.info("------------------------------------------------------------")
        
        try:
            # Настраиваем бота
            await self.setup_bot()
            
            # Настраиваем webhook
            await self.setup_webhook()
            
            # Запускаем API сервер
            logger.info("🚀 Запуск API сервера с поддержкой webhook...")
            await self.start_api_server()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Остановка всех сервисов"""
        logger.info("🛑 Остановка сервисов...")
        self.running = False
        
        if self.bot:
            try:
                await self.bot.delete_webhook()
                logger.info("✅ Webhook удален")
                
                # Уведомляем админа об остановке
                try:
                    admin_ids = os.environ.get('ADMIN_IDS', '').split(',')
                    if admin_ids and admin_ids[0]:
                        await self.bot.send_message(
                            int(admin_ids[0]), 
                            "🛑 <b>Rubkoff Bot остановлен</b>\n\nДо свидания! 👋"
                        )
                except:
                    pass
                    
                await self.bot.session.close()
                logger.info("✅ Bot остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки бота: {e}")
        
        if self.api_server:
            try:
                self.api_server.should_exit = True
                logger.info("✅ API сервер остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки API сервера: {e}")


def signal_handler(signum, frame):
    """Обработчик сигналов для корректной остановки"""
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    sys.exit(0)


async def main():
    """Главная функция"""
    
    # Проверяем токен бота
    if os.environ.get('BOT_TOKEN') == 'YOUR_REAL_BOT_TOKEN_HERE':
        logger.error("❌ ОШИБКА: Не указан реальный BOT_TOKEN!")
        logger.error("📝 Откройте файл run_tunnel4_bot.py и замените:")
        logger.error("   BOT_TOKEN='YOUR_REAL_BOT_TOKEN_HERE'")
        logger.error("   на ваш реальный токен от @BotFather")
        return 1
    
    # Настраиваем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    launcher = RubkoffLauncher()
    
    try:
        await launcher.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    finally:
        await launcher.stop()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("✅ Сервисы остановлены пользователем")
        sys.exit(0) 