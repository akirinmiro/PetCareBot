from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import Pet

def get_yes_no_vaccination_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="yes_vaccination"),
                InlineKeyboardButton(text="❌ Нет", callback_data="no_vaccination")
            ]
        ]
    )

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐾 Профиль"), KeyboardButton(text="📚 Справка")],
            [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="➕ Добавить питомца")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )

def get_pet_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐱 Кошка"), KeyboardButton(text="🐶 Собака")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_info_pet_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐱 Кошка"), KeyboardButton(text="🐶 Собака")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_info_category_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Уход"), KeyboardButton(text="🎾 Игры")],
            [KeyboardButton(text="💊 Здоровье")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_breeds_keyboard(pet_type: str):
    breeds = {
        "кошка": ["Британская", "Сиамская", "Мейн-кун"],
        "собака": ["Лабрадор", "Овчарка", "Бульдог"]
    }.get(pet_type, [])

    buttons = [KeyboardButton(text=breed) for breed in breeds]
    buttons.append(KeyboardButton(text="Без породы"))
    buttons.append(KeyboardButton(text="🔙 Назад"))
    buttons.append(KeyboardButton(text="🔙 Главное меню"))

    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_back_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_reminder_options():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить напоминание"), KeyboardButton(text="Мои напоминания")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_days_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пн"), KeyboardButton(text="Вт"), KeyboardButton(text="Ср")],
            [KeyboardButton(text="Чт"), KeyboardButton(text="Пт"), KeyboardButton(text="Сб")],
            [KeyboardButton(text="Вс"), KeyboardButton(text="Ежедневно")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_reminder_actions_keyboard(reminder_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Время", callback_data=f"edit_time_{reminder_id}"),
                InlineKeyboardButton(text="📅 Дни", callback_data=f"edit_days_{reminder_id}")
            ],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_reminder_{reminder_id}")]
        ]
    )

def get_pet_management_keyboard(pet: Pet):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить дату",
                    callback_data=f"edit_vacc_{pet.id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"delete_pet_{pet.id}"
                )
            ]
        ]
    )

def get_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )