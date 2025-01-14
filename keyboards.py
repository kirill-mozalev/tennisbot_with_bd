from telegram import ReplyKeyboardMarkup

def get_main_menu_keyboard():
    """Клавиатура для главного меню."""
    keyboard = [
        ["Начать игру"],
        ["Завершить игру"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_winner_keyboard(player1, player2):
    """Клавиатура для выбора победителя."""
    keyboard = [
        [player1, player2],
        ["Пропустить матч"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_new_round_keyboard():
    """Клавиатура для нового круга."""
    keyboard = [
        ["Новый круг", "Завершить игру"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_end_game_keyboard():
    """Клавиатура после завершения игры."""
    keyboard = [
        ["Начать новую игру"],  # Кнопка для новой игры
        ["Статистика"]  # Кнопка для просмотра статистики
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_play_match_keyboard():
    """Клавиатура для состояния PLAY_MATCH."""
    keyboard = [
        ["Пропустить матч"],
        ["Завершить игру сейчас"]  # Новая кнопка
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)