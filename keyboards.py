# keyboards.py
from telegram import ReplyKeyboardMarkup

def get_main_menu_keyboard():
    """Клавиатура для главного меню."""
    keyboard = [
        ["Начать игру", "Статистика"],
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