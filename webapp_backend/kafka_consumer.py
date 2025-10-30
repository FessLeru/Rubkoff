"""
Kafka consumer для получения результатов опросов
"""

import asyncio
import json
import logging
from typing import Dict, Any
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)


class SurveyKafkaConsumer:
    """Consumer для обработки результатов опросов из Kafka"""
    
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer: AIOKafkaConsumer = None
        self.running = False
    
    async def start(self) -> None:
        """Запуск consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='rubkoff_backend'
            )
            await self.consumer.start()
            self.running = True
            logger.info(f"Kafka consumer started, topic: {self.topic}")
            
            # Запуск обработки сообщений
            await self._consume_messages()
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self) -> None:
        """Остановка consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def _consume_messages(self) -> None:
        """Обработка сообщений из Kafka"""
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                    
                try:
                    await self._process_survey_result(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in consumer: {e}")
    
    async def _process_survey_result(self, data: Dict[str, Any]) -> None:
        """Обработка результата опроса"""
        try:
            user_id = data.get('user_id')
            timestamp = data.get('timestamp')
            conversation_history = data.get('conversation_history', [])
            recommended_houses = data.get('recommended_houses', [])
            survey_type = data.get('survey_type', 'house_selection')
            
            logger.info(f"Processing survey result for user {user_id}")
            logger.info(f"Survey type: {survey_type}")
            logger.info(f"Recommended houses count: {len(recommended_houses)}")
            logger.info(f"Conversation history length: {len(conversation_history)}")

            await self._save_survey_data(user_id, data)
            
        except Exception as e:
            logger.error(f"Error processing survey result: {e}")
    
    async def _save_survey_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Сохранение данных опроса (заглушка)"""
        # Здесь должна быть логика сохранения в базу данных
        logger.info(f"Survey data saved for user {user_id}")
        
        # Пример: можно добавить сохранение в базу данных
        # from core.db import get_session
        # async with get_session() as session:
        #     # Сохранение данных опроса
        #     pass


# Глобальный экземпляр consumer
survey_consumer = SurveyKafkaConsumer(
    bootstrap_servers="kafka:9092",
    topic="survey_results"
)
