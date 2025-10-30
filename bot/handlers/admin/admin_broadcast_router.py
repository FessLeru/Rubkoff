import logging
import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import User
from bot.states import BroadcastStates
from bot.keyboards import get_back_to_admin_keyboard
from utils.helpers import log_user_action, is_admin
from core.config import config

logger = logging.getLogger(__name__)

# Create router for admin broadcast handlers
router = Router()


@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Start broadcast message creation"""
    try:
        if not callback.from_user:
            await callback.answer("Error: User not found")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            await callback.answer("❌ У вас нет прав для этого действия")
            return

        await state.set_state(BroadcastStates.waiting_for_content)
        
        kb = InlineKeyboardBuilder()
        kb.button(text="❌ Отмена", callback_data="admin:cancel_broadcast")
        kb.button(text="⬅️ Назад", callback_data="admin:back_to_admin")
        
        await callback.message.edit_text(
            "📨 <b>Создание рассылки</b>\n\n"
            "Отправьте сообщение, которое нужно разослать всем пользователям.\n"
            "Это может быть:\n"
            "• Текст\n"
            "• Фото\n"
            "• Видео\n"
            "• Голосовое сообщение\n"
            "• Видеокружок\n"
            "• Документ\n"
            "• Аудио\n\n"
            "Бот автоматически определит тип сообщения.",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error starting broadcast: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при создании рассылки")


@router.message(BroadcastStates.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Process broadcast message content"""
    try:
        if not message.from_user:
            return

        user_is_admin = await is_admin(message.from_user.id, session)
        if not user_is_admin:
            await message.answer("❌ Доступ запрещен")
            return

        # Store the message content and type for broadcasting
        broadcast_data = {}

        if message.text and not message.photo and not message.video and not message.video_note and not message.voice and not message.document and not message.audio:
            broadcast_data["type"] = "text"
            broadcast_data["content"] = message.text
        elif message.photo:
            broadcast_data["type"] = "photo"
            broadcast_data["file_id"] = message.photo[-1].file_id
            broadcast_data["caption"] = message.caption or ""
        elif message.video:
            broadcast_data["type"] = "video"
            broadcast_data["file_id"] = message.video.file_id
            broadcast_data["caption"] = message.caption or ""
        elif message.video_note:
            broadcast_data["type"] = "video_note"
            broadcast_data["file_id"] = message.video_note.file_id
        elif message.document:
            broadcast_data["type"] = "document"
            broadcast_data["file_id"] = message.document.file_id
            broadcast_data["caption"] = message.caption or ""
        elif message.audio:
            broadcast_data["type"] = "audio"
            broadcast_data["file_id"] = message.audio.file_id
            broadcast_data["caption"] = message.caption or ""
        elif message.voice:
            broadcast_data["type"] = "voice"
            broadcast_data["file_id"] = message.voice.file_id
            broadcast_data["caption"] = message.caption or ""
        else:
            await message.answer("❌ Этот тип сообщения не поддерживается для рассылки.")
            return

        # Get users count
        users_count = await session.scalar(
            select(func.count(User.id))
            .where(User.is_blocked == False)
        )

        # Save message data to state
        await state.update_data(broadcast_message=broadcast_data)
        await state.set_state(BroadcastStates.confirmation)

        # Create confirmation keyboard
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Подтвердить", callback_data="admin:confirm_broadcast")
        kb.button(text="❌ Отмена", callback_data="admin:cancel_broadcast")
        kb.button(text="⬅️ Назад", callback_data="admin:back_to_admin")
        kb.adjust(2, 1)

        await message.answer(
            f"🔍 <b>Предпросмотр рассылки</b>\n\n"
            f"Тип контента: {broadcast_data['type']}\n"
            f"Сообщение будет отправлено {users_count} пользователям.\n\n"
            f"Подтвердите отправку:",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

        # Forward the message back to admin for preview
        await message.forward(chat_id=message.from_user.id)

    except Exception as e:
        logger.error(f"Error processing broadcast content: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке сообщения")


@router.callback_query(F.data == "admin:confirm_broadcast")
async def send_broadcast(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    """Send broadcast message to all users"""
    try:
        if not callback.from_user:
            await callback.answer("Error: Invalid callback")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            await callback.answer("❌ Доступ запрещен")
            return

        # Get stored message data
        data = await state.get_data()
        broadcast_data = data.get("broadcast_message")
        if not broadcast_data:
            await callback.answer("❌ Данные для рассылки не найдены")
            return

        await callback.message.edit_text("⏳ Выполняется рассылка...")

        # Get active users
        result = await session.execute(
            select(User.user_id)
            .where(User.is_blocked == False)
        )
        user_ids = [row[0] for row in result.fetchall()]

        total_users = len(user_ids)
        success_count = 0
        failed_count = 0
        start_time = datetime.utcnow()

        # Send messages in chunks
        for i in range(0, total_users, config.MAX_BROADCAST_CHUNK_SIZE):
            chunk = user_ids[i:i + config.MAX_BROADCAST_CHUNK_SIZE]
            
            for user_id in chunk:
                try:
                    if broadcast_data["type"] == "text":
                        await bot.send_message(user_id, broadcast_data["content"])
                    elif broadcast_data["type"] == "photo":
                        await bot.send_photo(
                            user_id,
                            broadcast_data["file_id"],
                            caption=broadcast_data.get("caption")
                        )
                    elif broadcast_data["type"] == "video":
                        await bot.send_video(
                            user_id,
                            broadcast_data["file_id"],
                            caption=broadcast_data.get("caption")
                        )
                    elif broadcast_data["type"] == "video_note":
                        await bot.send_video_note(user_id, broadcast_data["file_id"])
                    elif broadcast_data["type"] == "document":
                        await bot.send_document(
                            user_id,
                            broadcast_data["file_id"],
                            caption=broadcast_data.get("caption")
                        )
                    elif broadcast_data["type"] == "audio":
                        await bot.send_audio(
                            user_id,
                            broadcast_data["file_id"],
                            caption=broadcast_data.get("caption")
                        )
                    elif broadcast_data["type"] == "voice":
                        await bot.send_voice(
                            user_id,
                            broadcast_data["file_id"],
                            caption=broadcast_data.get("caption")
                        )
                    
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error sending broadcast to user {user_id}: {e}")
                    failed_count += 1
                    
                    # Mark user as blocked if appropriate
                    error_message = str(e).lower()
                    if "blocked" in error_message or "bot was blocked" in error_message or "user is deactivated" in error_message:
                        try:
                            result = await session.execute(
                                select(User).where(User.user_id == user_id)
                            )
                            user = result.scalar_one_or_none()
                            if user:
                                user.is_blocked = True
                                await session.commit()
                        except Exception as db_error:
                            logger.error(f"Error updating user blocked status: {db_error}")

                await asyncio.sleep(config.BROADCAST_DELAY)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Log action
        await log_user_action(
            user_id=callback.from_user.id,
            action=f"broadcast_{broadcast_data['type']}",
            session=session
        )

        # Clear state
        await state.clear()

        # Show results
        status_message = (
            f"✅ <b>Рассылка выполнена</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Успешно отправлено: {success_count}\n"
            f"❌ Не отправлено: {failed_count}\n"
            f"⏱ Время выполнения: {duration:.1f} сек."
        )

        await callback.message.edit_text(
            status_message,
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error sending broadcast: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при отправке рассылки")
        await state.clear()


@router.callback_query(F.data == "admin:cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel broadcast sending"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Рассылка отменена",
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error canceling broadcast: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при отмене рассылки")
