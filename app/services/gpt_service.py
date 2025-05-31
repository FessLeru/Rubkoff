from typing import List, Dict, Any, Optional
import logging
import openai
from openai import AsyncOpenAI

from app.core.config import config

logger = logging.getLogger(__name__)

class GPTService:
    """Service for interacting with OpenAI GPT API"""
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.temperature = config.OPENAI_TEMPERATURE

    async def chat_with_gpt(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        houses: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate response using GPT model"""
        try:
            # Add house information to system message
            house_info = "\n".join([
                f"Дом {h['id']}: {h['name']}, {h['area']}м², "
                f"{h['floors']} этаж{'а' if h['floors'] in [2,3,4] else 'ей' if h['floors'] > 4 else ''}, "
                f"цена: {h['price']}₽"
                for h in houses
            ])
            
            system_message = {
                "role": "system",
                "content": (
                    "Ты — помощник по подбору домов от компании Rubkoff. "
                    "Твоя задача — помочь клиенту выбрать идеальный дом, "
                    "задавая уточняющие вопросы о его предпочтениях.\n\n"
                    f"Доступные дома:\n{house_info}"
                )
            }
            
            # Prepare messages for API
            messages = [system_message] + conversation_history[-10:]  # Keep last 10 messages
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat_with_gpt: {e}", exc_info=True)
            return None

    async def find_best_house(
        self,
        conversation_history: List[Dict[str, str]],
        houses: List[Dict[str, Any]]
    ) -> Optional[int]:
        """Find best matching house based on conversation"""
        try:
            # Extract user preferences from conversation
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in conversation_history
            ])
            
            system_message = {
                "role": "system",
                "content": (
                    "На основе диалога с клиентом выбери ID наиболее подходящего дома. "
                    "Ответь только номером ID дома, без дополнительного текста."
                )
            }
            
            user_message = {
                "role": "user",
                "content": (
                    f"Диалог с клиентом:\n{conversation_text}\n\n"
                    f"Доступные дома:\n" + "\n".join([
                        f"ID {h['id']}: {h['name']}, {h['area']}м², "
                        f"{h['floors']} этаж{'а' if h['floors'] in [2,3,4] else 'ей' if h['floors'] > 4 else ''}, "
                        f"цена: {h['price']}₽"
                        for h in houses
                    ])
                )
            }
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[system_message, user_message],
                max_tokens=50,
                temperature=0.3
            )
            
            # Extract house ID from response
            try:
                house_id = int(response.choices[0].message.content.strip())
                if any(h["id"] == house_id for h in houses):
                    return house_id
            except (ValueError, AttributeError):
                logger.error("Failed to parse house ID from GPT response")
                
            return houses[0]["id"]  # Fallback to first house
            
        except Exception as e:
            logger.error(f"Error in find_best_house: {e}", exc_info=True)
            return None

# Create global instance
gpt_service = GPTService()

# Export functions for backward compatibility
async def chat_with_gpt(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    houses: List[Dict[str, Any]]
) -> Optional[str]:
    return await gpt_service.chat_with_gpt(user_message, conversation_history, houses)

async def find_best_house(
    conversation_history: List[Dict[str, str]],
    houses: List[Dict[str, Any]]
) -> Optional[int]:
    return await gpt_service.find_best_house(conversation_history, houses) 