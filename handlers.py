import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters
from database import create_connection
from utils import generate_matches, get_session_stats, get_current_round_stats,get_monthly_stats
from keyboards import get_main_menu_keyboard, get_winner_keyboard, get_new_round_keyboard, get_end_game_keyboard


# Настроим логгер
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
REGISTER_PLAYERS, GENERATE_GRID, PLAY_MATCH, VIEW_STATS = range(4)

async def start(update: Update, context: CallbackContext) -> int:
    """Обработчик для команды /start."""
    logger.info(f"Начата новая сессия в чате {update.message.chat_id}.")
    await update.message.reply_text(
        "Привет! Давай начнем новую сессию. Введи имена игроков через запятую.",
        reply_markup=get_main_menu_keyboard()
    )
    return REGISTER_PLAYERS

async def register_players(update: Update, context: CallbackContext) -> int:
    """Регистрирует игроков и создает сессию."""
    players = update.message.text.split(',')
    players = [player.strip() for player in players if player.strip()]

    if len(players) < 2:
        logger.warning(f"Недостаточно игроков в чате {update.message.chat_id}.")
        await update.message.reply_text("Нужно как минимум два игрока. Попробуй еще раз.")
        return REGISTER_PLAYERS

    conn = create_connection()
    cursor = conn.cursor()

    chat_id = update.message.chat_id
    cursor.execute('INSERT INTO sessions (chat_id) VALUES (?)', (chat_id,))
    session_id = cursor.lastrowid

    for player in players:
        cursor.execute('INSERT INTO players (session_id, name) VALUES (?, ?)', (session_id, player))

    conn.commit()
    conn.close()

    context.user_data['session_id'] = session_id
    logger.info(f"Игроки зарегистрированы в сессии {session_id}: {', '.join(players)}.")
    await update.message.reply_text(f"Игроки зарегистрированы: {', '.join(players)}. Генерируем сетку...")

    return await generate_grid(update, context)

async def generate_grid(update: Update, context: CallbackContext) -> int:
    """Генерирует сетку матчей для текущего круга."""
    session_id = context.user_data['session_id']
    round_number = context.user_data.get('round_number', 1)

    # Увеличиваем номер круга на 1
    round_number += 1
    context.user_data['round_number'] = round_number

    generate_matches(session_id, round_number)

    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT p1.name, p2.name
    FROM matches m
    JOIN players p1 ON m.player1_id = p1.player_id
    JOIN players p2 ON m.player2_id = p2.player_id
    WHERE m.session_id = ? AND m.round_number = ?
    ''', (session_id, round_number))
    matches = cursor.fetchall()

    grid_text = "Сетка матчей:\n"
    for match in matches:
        grid_text += f"{match[0]} vs {match[1]}\n"

    logger.info(f"Сетка матчей сгенерирована для сессии {session_id}, круг {round_number}.")
    await update.message.reply_text(grid_text)
    await update.message.reply_text("Нажми 'Начать игру' чтобы начать игру.", reply_markup=get_main_menu_keyboard())

    conn.close()
    return PLAY_MATCH


async def play_match(update: Update, context: CallbackContext) -> int:
    """Обрабатывает текущий матч и запрашивает победителя."""
    session_id = context.user_data['session_id']
    logger.debug(f"Текущий session_id: {session_id}")

    conn = create_connection()
    cursor = conn.cursor()

    # Получаем следующий матч без победителя или пропущенный матч
    cursor.execute(''' 
    SELECT match_id, player1_id, player2_id FROM matches
    WHERE session_id = ? AND winner_id IS NULL AND is_skipped = 0
    LIMIT 1
    ''', (session_id,))
    match = cursor.fetchone()

    if not match:
        # Если нет матчей без победителя, проверяем пропущенные
        cursor.execute('''
        SELECT match_id, player1_id, player2_id FROM matches
        WHERE session_id = ? AND winner_id IS NULL AND is_skipped = 1
        LIMIT 1
        ''', (session_id,))
        match = cursor.fetchone()

        if not match:
            logger.info(f"Все матчи круга сыграны в сессии {session_id}.")
            await update.message.reply_text("Все матчи круга сыграны. Вот статистика за круг:",
                                            reply_markup=get_main_menu_keyboard())
            return await view_stats(update, context)

    match_id, player1_id, player2_id = match

    # Получаем имена игроков
    cursor.execute('SELECT name FROM players WHERE player_id IN (?, ?)', (player1_id, player2_id))
    player1, player2 = cursor.fetchall()

    # Сохраняем текущий матч в контексте
    context.user_data['current_match'] = (match_id, player1[0], player2[0])

    # Создаем клавиатуру с именами игроков и кнопкой "Завершить игру сейчас"
    keyboard = [
        [player1[0], player2[0]],
        ["Пропустить матч"],
        ["Завершить игру сейчас"]  # Новая кнопка
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    logger.info(f"Начат матч {player1[0]} vs {player2[0]} в сессии {session_id}.")
    await update.message.reply_text(
        f"Кто победил в матче {player1[0]} vs {player2[0]}?",
        reply_markup=reply_markup
    )

    conn.close()
    return PLAY_MATCH


async def handle_winner(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор победителя и переходит к следующему матчу."""
    winner_name = update.message.text
    match_id, player1, player2 = context.user_data['current_match']

    if winner_name == "Пропустить матч":
        logger.info(f"Матч {player1} vs {player2} пропущен в сессии {context.user_data['session_id']}.")

        # Помечаем матч как пропущенный
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE matches SET is_skipped = 1 WHERE match_id = ?', (match_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text("Матч пропущен.", reply_markup=get_main_menu_keyboard())
        return await play_match(update, context)  # Переходим к следующему матчу

    conn = create_connection()
    cursor = conn.cursor()

    # Получаем ID победителя
    cursor.execute('SELECT player_id FROM players WHERE name = ? AND session_id = ?',
                   (winner_name, context.user_data['session_id']))
    winner = cursor.fetchone()

    if winner:
        winner_id = winner[0]
        cursor.execute('UPDATE matches SET winner_id = ? WHERE match_id = ?', (winner_id, match_id))
        conn.commit()
        logger.info(f"Победитель {winner_name} сохранен в матче {player1} vs {player2}.")
        await update.message.reply_text(f"Победитель {winner_name} сохранен. Следующий матч...",
                                        reply_markup=get_main_menu_keyboard())
    else:
        logger.warning(f"Ошибка: игрок {winner_name} не найден в сессии {context.user_data['session_id']}.")
        await update.message.reply_text("Ошибка: игрок не найден.", reply_markup=get_main_menu_keyboard())

    conn.close()
    return await play_match(update, context)


async def view_stats(update: Update, context: CallbackContext) -> int:
    """Показывает статистику за текущий круг и общую статистику."""
    session_id = context.user_data['session_id']
    round_number = context.user_data.get('round_number', 1)

    # Получаем статистику за текущий круг
    stats_current_round = get_current_round_stats(session_id, round_number)
    stats_text_current = "Статистика за текущий круг:\n"
    for player, wins in stats_current_round:
        stats_text_current += f"{player}: {wins} побед\n"

    # Получаем общую статистику за все круги
    stats_total = get_session_stats(session_id)
    stats_text_total = "Общая статистика за игру:\n"
    for player, wins in stats_total:
        stats_text_total += f"{player}: {wins} побед\n"

    # Выводим оба сообщения
    await update.message.reply_text(stats_text_current, reply_markup=get_new_round_keyboard())
    await update.message.reply_text(stats_text_total, reply_markup=get_new_round_keyboard())

    return VIEW_STATS

async def end_game(update: Update, context: CallbackContext) -> int:
    """Завершает игру и показывает клавиатуру с кнопкой 'Начать новую игру'."""
    session_id = context.user_data.get('session_id', None)
    logger.info(f"Игра завершена в сессии {session_id}.")

    # Очищаем только данные, связанные с текущей игрой
    if 'session_id' in context.user_data:
        del context.user_data['session_id']
    if 'round_number' in context.user_data:
        del context.user_data['round_number']

    # Показать клавиатуру с кнопкой "Начать новую игру"
    reply_markup = get_end_game_keyboard()
    await update.message.reply_text(
        "Игра завершена. Нажми 'Начать новую игру', чтобы зарегистрировать новых игроков.",
        reply_markup=reply_markup
    )

    # Возвращаемся в состояние VIEW_STATS, чтобы кнопка "Статистика" работала
    return VIEW_STATS


async def force_end_game(update: Update, context: CallbackContext) -> int:
    """Принудительное завершение игры и вывод статистики."""
    logger.debug("force_end_game started.")

    session_id = context.user_data.get('session_id')
    logger.debug(f"session_id: {session_id}")

    if not session_id:
        logger.debug("Session not found.")
        await update.message.reply_text("Сессия не найдена. Начните новую игру.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    # Получаем статистику за текущий круг
    round_number = context.user_data.get('round_number', 1)
    stats_current_round = get_current_round_stats(session_id, round_number)
    logger.debug(f"Stats for current round: {stats_current_round}")

    stats_text_current = "Статистика за текущий круг:\n"
    if stats_current_round:
        for player, wins in stats_current_round:
            stats_text_current += f"{player}: {wins} побед\n"
    else:
        stats_text_current += "Нет данных для текущего круга.\n"

    # Получаем общую статистику за всю игру
    stats_total = get_session_stats(session_id)
    logger.debug(f"Total stats: {stats_total}")

    stats_text_total = "Общая статистика за игру:\n"
    if stats_total:
        for player, wins in stats_total:
            stats_text_total += f"{player}: {wins} побед\n"
    else:
        stats_text_total += "Нет общей статистики.\n"

    # Отправляем статистику текущего круга и всей игры
    await update.message.reply_text(stats_text_current)
    await update.message.reply_text(stats_text_total)

    # Очищаем данные пользователя
    if 'session_id' in context.user_data:
        del context.user_data['session_id']
    if 'round_number' in context.user_data:
        del context.user_data['round_number']
    logger.debug("User data cleared.")

    # Показываем клавиатуру с кнопками "Начать новую игру" и "Статистика"
    await update.message.reply_text(
        "Игра завершена. Выберите действие:",
        reply_markup=get_end_game_keyboard()
    )

    logger.debug("End game keyboard sent.")

    # Возвращаем пользователя в состояние VIEW_STATS, чтобы кнопка "Статистика" работала
    return VIEW_STATS

async def show_monthly_stats(update: Update, context: CallbackContext) -> int:
    """Показывает статистику игроков и их побед за текущий месяц."""
    chat_id = update.message.chat_id

    # Получаем статистику за текущий месяц
    stats = get_monthly_stats(chat_id)

    if not stats:
        await update.message.reply_text("В текущем месяце ещё нет данных о победителях.")
        return VIEW_STATS

    # Формируем текст для вывода статистики
    stats_text = "Статистика за текущий месяц:\n"
    for player, wins in stats:
        stats_text += f"{player}: {wins} побед\n"

    # Отправляем статистику пользователю
    await update.message.reply_text(stats_text, reply_markup=get_end_game_keyboard())

    return VIEW_STATS