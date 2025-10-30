from typing import List, Dict, Any, Optional
import logging
import asyncio
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import config
from utils.error_handlers import with_error_handling, GPTError

logger = logging.getLogger(__name__)

class GPTService:
    """Service for interacting with OpenAI GPT API"""
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.temperature = config.OPENAI_TEMPERATURE
        self.max_retries = 3
        self.max_history = 10  # Limit conversation history
        self.timeout = 30  # 30 seconds timeout
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda _: None  # Return None on all retries failed
    )
    @with_error_handling("Failed to chat with GPT")
    async def chat_with_gpt(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        houses: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate response using GPT model with retries and timeout"""
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
            
            # Keep last N messages to avoid context length issues
            messages = [system_message] + conversation_history[-self.max_history:]
            
            async with asyncio.timeout(self.timeout):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                if not response.choices:
                    raise GPTError(
                        message="Empty response from GPT",
                        user_message="Извините, не удалось получить ответ. Попробуйте позже."
                    )
                
                return response.choices[0].message.content
                
        except asyncio.TimeoutError:
            raise GPTError(
                message="GPT request timeout",
                user_message="Извините, сервис временно перегружен. Попробуйте позже."
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda _: None
    )
    @with_error_handling("Failed to find best house")
    async def find_best_house(
        self,
        conversation_history: List[Dict[str, str]],
        houses: List[Dict[str, Any]]
    ) -> Optional[int]:
        """Find best matching house based on conversation with retries"""
        try:
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in conversation_history[-self.max_history:]  # Limit history
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
            
            async with asyncio.timeout(self.timeout):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[system_message, user_message],
                    max_tokens=50,
                    temperature=0.3
                )
                
                if not response.choices:
                    raise GPTError(
                        message="Empty response from GPT",
                        user_message="Извините, не удалось подобрать дом. Попробуйте позже."
                    )
                
                try:
                    house_id = int(response.choices[0].message.content.strip())
                    if any(h["id"] == house_id for h in houses):
                        return house_id
                except (ValueError, AttributeError):
                    logger.error("Failed to parse house ID from GPT response")
                    
                # Fallback to first house if parsing failed
                return houses[0]["id"] if houses else None
                
        except asyncio.TimeoutError:
            raise GPTError(
                message="GPT request timeout",
                user_message="Извините, сервис временно перегружен. Попробуйте позже."
            )
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self.client, 'close'):
            await self.client.close()

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