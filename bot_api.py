# bot_api.py - новая версия бота на SStats API
import os
import asyncio
from datetime import datetime
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from sstats_client import SStatsClient
from match_predictor_api import get_top_bets_api, analyze_match

# ============ КОНФИГУРАЦИЯ ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Токен не найден")
    exit(1)

API_KEY = "g69egm3kibyrr20e"  # ваш ключ
client = SStatsClient(API_KEY)

# Кэш для данных (чтобы не дёргать API при каждом запросе)
matches_cache = {}
stats_cache = {}

# ============ КОМАНДЫ БОТА ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "⚽ *Футбольный аналитический бот (API версия)*\n\n"
        "Я анализирую матчи с помощью SStats API\n\n"
        "📋 *Доступные команды:*\n"
        "• `/today` - матчи на сегодня\n"
        "• `/best_bets` - лучшие ставки на сегодня\n"
        "• `/preview <матч>` - детальный анализ матча\n"
        "• `/search <команда>` - поиск команды\n\n"
        "⚠️ *Данные носят информационный характер*",
        parse_mode='Markdown'
    )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает матчи на сегодня"""
    await update.message.reply_text("🔄 Загружаю матчи на сегодня...")
    
    matches = client.get_today_matches(limit=30)
    
    if not matches:
        await update.message.reply_text("❌ Не удалось загрузить матчи")
        return
    
    # Сохраняем в кэш
    matches_cache[update.effective_user.id] = matches
    
    # Создаём клавиатуру
    keyboard = []
    for match in matches[:15]:  # ограничиваем для удобства
        home = match.get('homeTeam', {}).get('name', '?')
        away = match.get('awayTeam', {}).get('name', '?')
        game_id = match.get('id')
        button_text = f"{home} vs {away}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"preview_{game_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Найдено матчей: {len(matches)}\n\n⚽ Выберите матч для анализа:",
        reply_markup=reply_markup
    )

async def best_bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает лучшие ставки на сегодня"""
    await update.message.reply_text("🔄 Анализирую матчи...")
    
    top_bets = get_top_bets_api(client, limit=5)
    
    if not any(top_bets.values()):
        await update.message.reply_text("❌ Не найдено подходящих матчей")
        return
    
    message = "🎯 *ЛУЧШИЕ СТАВКИ НА СЕГОДНЯ*\n\n"
    
    # BTTS
    if top_bets.get('btts'):
        message += "⚽ *ОБЕ ЗАБЬЮТ (BTTS)*\n"
        for match in top_bets['btts'][:3]:
            stars = '⭐' * min(5, match['btts_score'] // 2)
            message += f"• {match['match']} — {stars} ({match['btts_score']}/10)\n"
        message += "\n"
    
    # OVER25
    if top_bets.get('over25'):
        message += "📊 *ТОТАЛ БОЛЬШЕ 2.5*\n"
        for match in top_bets['over25'][:3]:
            message += f"• {match['match']} — {match['over25_score']}/10\n"
        message += "\n"
    
    # УГЛОВЫЕ
    if top_bets.get('corners'):
        message += "🚩 *УГЛОВЫЕ > 8.5*\n"
        for match in top_bets['corners'][:3]:
            message += f"• {match['match']} — {match['corners_score']}/10\n"
        message += "\n"
    
    # ЖК
    if top_bets.get('yellow'):
        message += "🟨 *ЖК > 4.5*\n"
        for match in top_bets['yellow'][:3]:
            message += f"• {match['match']} — {match['yellow_score']}/10\n"
        message += "\n"
    
    message += "---\n⚠️ Прогнозы основаны на статистике последних 10 матчей"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на матч"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("preview_", "")
    
    await query.edit_message_text(f"📊 Анализирую матч...")
    
    # Получаем статистику матча
    stats = client.get_match_stats(game_id, limit=10)
    
    if not stats or not stats.get('home'):
        await query.edit_message_text("❌ Не удалось получить статистику матча")
        return
    
    # Находим матч в кэше или загружаем
    matches = client.get_today_matches(limit=30)
    match = None
    for m in matches:
        if str(m.get('id')) == str(game_id):
            match = m
            break
    
    if not match:
        await query.edit_message_text("❌ Матч не найден")
        return
    
    # Анализируем
    analysis = analyze_match(match, stats)
    
    # Формируем сообщение
    message = f"⚽ *ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА*\n\n"
    message += f"🔴 *{match.get('homeTeam', {}).get('name')}* vs 🔵 *{match.get('awayTeam', {}).get('name')}*\n\n"
    
    message += f"📊 *Форма команд (последние 10 матчей)*\n"
    message += f"🏠 Хозяева: {analysis['home_form']} | ⚽ {analysis['home_goals']:.1f} гола\n"
    message += f"✈️ Гости: {analysis['away_form']} | ⚽ {analysis['away_goals']:.1f} гола\n\n"
    
    message += f"🎯 *ПРОГНОЗЫ*\n"
    message += f"• Обе забьют: {analysis['btts_score']}/10\n"
    message += f"• Тотал > 2.5: {analysis['over25_score']}/10\n"
    if analysis['corners_score'] > 0:
        message += f"• Угловые > 8.5: {analysis['corners_score']}/10\n"
    if analysis['yellow_score'] > 0:
        message += f"• ЖК > 4.5: {analysis['yellow_score']}/10\n"
    
    message += f"\n📅 {analysis['date']}"
    
    await query.edit_message_text(message, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск команды"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название команды\n"
            "Пример: `/search Арсенал`",
            parse_mode='Markdown'
        )
        return
    
    query = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Ищу команду '{query}'...")
    
    # Пока поиск через API не реализован, предлагаем выбрать из матчей
    matches = client.get_today_matches(limit=30)
    found = []
    
    for match in matches:
        home = match.get('homeTeam', {}).get('name', '')
        away = match.get('awayTeam', {}).get('name', '')
        if query.lower() in home.lower() or query.lower() in away.lower():
            found.append(match)
    
    if not found:
        await update.message.reply_text(f"❌ Команда '{query}' не найдена в сегодняшних матчах")
        return
    
    keyboard = []
    for match in found[:10]:
        home = match.get('homeTeam', {}).get('name', '?')
        away = match.get('awayTeam', {}).get('name', '?')
        game_id = match.get('id')
        keyboard.append([InlineKeyboardButton(f"{home} vs {away}", callback_data=f"preview_{game_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"✅ Найдено матчей с участием '{query}': {len(found)}\n\nВыберите матч для анализа:",
        reply_markup=reply_markup
    )

# ============ ЗАПУСК БОТА ============

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("best_bets", best_bets_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CallbackQueryHandler(preview_callback, pattern="preview_"))
    
    print("🚀 Бот (API версия) запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()