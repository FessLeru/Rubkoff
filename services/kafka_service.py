"""
Сервис для работы с Kafka
"""

import json
import logging
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from core.config import config

logger = logging.getLogger(__name__)


class KafkaService:
    """Сервис для отправки данных в Kafka"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
    
    async def start(self) -> None:
        """Запуск Kafka producer"""
        if not config.KAFKA_ENABLED:
            logger.info("Kafka disabled in config")
            return
            
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self.producer.start()
            logger.info(f"Kafka producer started, topic: {config.KAFKA_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.producer = None
    
    async def stop(self) -> None:
        """Остановка Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send_survey_result(self, user_id: int, survey_data: Dict[str, Any]) -> bool:
        """Отправка результата опроса в Kafka"""
        if not config.KAFKA_ENABLED or not self.producer:
            logger.debug("Kafka not available, skipping message")
            return False
        
        try:
            message = {
                "user_id": user_id,
                "timestamp": survey_data.get("timestamp"),
                "conversation_history": survey_data.get("conversation_history", []),
                "recommended_houses": survey_data.get("houses", []),
                "survey_type": "house_selection"
            }
            
            await self.producer.send_and_wait(config.KAFKA_TOPIC, message)
            logger.info(f"Survey result sent to Kafka for user {user_id}")
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error sending survey result: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to Kafka: {e}")
            return False


# Глобальный экземпляр сервиса
kafka_service = KafkaService()
