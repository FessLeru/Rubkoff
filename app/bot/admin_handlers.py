from typing import Optional, List, Dict, Any
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Statistic, Admin
from app.bot.states import BroadcastStates
from app.bot.keyboards import (
    get_admin_panel_keyboard,
    get_back_to_admin_keyboard,
    get_broadcast_confirmation_keyboard
)
from app.services.scraper import parse_houses
from app.utils.helpers import log_user_action, is_admin
from app.core.config import config

logger = logging.getLogger(__name__)

# Create router for admin handlers
router = Router()

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle admin panel button click"""
    try:
        user_id = callback.from_user.id if callback.from_user else None
        logger.info(f"Processing admin panel access for user {user_id}")
        
        if not callback.from_user:
            logger.warning("No user information in callback")
            await callback.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            logger.warning(f"Unauthorized admin panel access attempt by user {callback.from_user.id}")
            await callback.answer("❌ У вас нет прав на доступ к панели администратора")
            return

        await callback.message.edit_text(
            "🔐 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        logger.info(f"Admin panel opened for user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin panel for user {callback.from_user.id if callback.from_user else 'unknown'}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при открытии панели администратора")

@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show bot statistics"""
    try:
        user_id = callback.from_user.id if callback.from_user else None
        logger.info(f"Processing stats request for user {user_id}")
        
        if not callback.from_user:
            logger.warning("No user information in callback")
            await callback.answer("Ошибка: не удалось получить информацию о пользователе")
            return

        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            logger.warning(f"Unauthorized stats access attempt by user {callback.from_user.id}")
            await callback.answer("❌ Доступ запрещен")
            return

        # Get total users count
        total_users = await session.scalar(select(func.count(User.id)))

        # Get active users (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        active_users = await session.scalar(
            select(func.count(User.id))
            .where(User.last_activity >= day_ago)
        )

        # Get today's statistics
        today = datetime.utcnow().date()
        today_stats = await session.scalar(
            select(func.count(Statistic.id))
            .where(func.date(Statistic.timestamp) == today)
        )

        # Get houses count
        houses_count = await session.scalar(text("SELECT COUNT(*) FROM houses"))

        stats_text = (
            "📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"📱 Активных за 24 часа: {active_users}\n"
            f"📈 Действий за сегодня: {today_stats}\n"
            f"🏠 Домов в каталоге: {houses_count}"
        )

        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
        logger.info(f"Stats shown to admin {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error showing stats for user {callback.from_user.id if callback.from_user else 'unknown'}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при получении статистики")

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

@router.callback_query(F.data == "admin:refresh")
async def refresh_catalog(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh houses catalog"""
    if not callback.from_user:
        await callback.answer("Error: User not found")
        return

    try:
        user_is_admin = await is_admin(callback.from_user.id, session)
        if not user_is_admin:
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.message.edit_text(
            "🔄 Обновление каталога домов...\n"
            "Пожалуйста, подождите."
        )

        houses_count = await parse_houses(session)
        
        await callback.message.edit_text(
            f"✅ Каталог обновлен\n\n"
            f"Загружено домов: {houses_count}",
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error refreshing catalog: {e}")
        await callback.answer("Произошла ошибка")

@router.callback_query(F.data == "admin:back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to admin panel"""
    await state.clear()
    await callback.message.edit_text(
        "🔐 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer() 