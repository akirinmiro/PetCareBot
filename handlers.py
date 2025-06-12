from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router
from database import Session, User, Pet, PetType, Reminder
from keyboards import *
from notifications import (
    scheduler,
    remove_reminder,
    schedule_jobs,
    schedule_vaccination_reminder
)
import re
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

class Form(StatesGroup):
    pet_type = State()
    pet_name = State()
    pet_breed = State()
    vaccination_date = State()
    confirm_notification = State()
    reminder_pet = State()
    reminder_time = State()
    reminder_days = State()
    edit_reminder_time = State()
    edit_reminder_days = State()
    edit_vaccination_date = State()
    info_pet_type = State()
    info_category = State()

@router.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    # Убираем приветственное сообщение при возврате в главное меню
    await message.answer(
        "Главное меню",
        reply_markup=get_main_menu()
    )

@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    # Оставляем приветствие только для команды /start
    await message.answer(
        "🐕🦺 Добро пожаловать в PetCareBot!",
        reply_markup=get_main_menu()
    )

@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    text = (
        "🤖 <b>PetCareBot</b> - ваш персональный помощник по уходу за питомцами\n"
        "📌 <b>Основные функции:</b>\n"
        "• Управление профилями питомцев\n"
        "• Настройка напоминаний о кормлении\n"
        "• Контроль вакцинации с напоминаниями\n"
    )
    await message.answer(text, reply_markup=get_main_menu())

@router.message(F.text == "🐾 Профиль")
async def profile(message: types.Message):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.pets:
            await message.answer("У вас пока нет добавленных питомцев", reply_markup=get_main_menu())
            return
        await message.answer("🐾 <b>Ваши питомцы:</b>")
        for pet in user.pets:
            text = f"▪️ <b>{pet.name}</b> ({pet.pet_type.value})"
            if pet.breed:
                text += f", порода: {pet.breed}"
            text += f"\n💉 Дата вакцинации: {pet.vaccination_date if pet.vaccination_date else 'не указана'}"
            await message.answer(text, reply_markup=get_pet_management_keyboard(pet))

@router.callback_query(F.data.startswith("delete_pet_"))
async def delete_pet_handler(query: CallbackQuery):
    try:
        pet_id = int(query.data.split("_")[2])
        with Session() as session:
            pet = session.query(Pet).filter_by(id=pet_id).first()
            if pet:
                for reminder in pet.reminders:
                    remove_reminder(reminder.id)
                    session.delete(reminder)
                pet_name = pet.name
                session.delete(pet)
                session.commit()
                try:
                    await query.message.delete()
                except:
                    pass
                await query.answer(f"✅ Питомец {pet_name} удален")
                await query.message.answer(
                    f"Питомец {pet_name} успешно удален",
                    reply_markup=get_main_menu()
                )
            else:
                await query.answer("Питомец не найден")
    except Exception as e:
        logger.error(f"Ошибка при удалении: {e}")
        await query.answer("Ошибка при удалении")

@router.message(F.text == "➕ Добавить питомца")
async def add_pet_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🐾 Выберите тип питомца:",
        reply_markup=get_pet_type_keyboard()
    )
    await state.set_state(Form.pet_type)

@router.message(Form.pet_type)
async def process_pet_type(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    pet_type = None
    if message.text == "🐱 Кошка":
        pet_type = PetType.CAT
    elif message.text == "🐶 Собака":
        pet_type = PetType.DOG

    if not pet_type:
        await message.answer("Пожалуйста, выберите тип из предложенных")
        return

    await state.update_data(pet_type=pet_type)
    await message.answer(
        "✏️ Введите имя питомца:",
        reply_markup=get_back_button()
    )
    await state.set_state(Form.pet_name)

@router.message(Form.pet_name)
async def process_pet_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text == "🔙 Назад":
        await message.answer(
            "🐾 Выберите тип питомца:",
            reply_markup=get_pet_type_keyboard()
        )
        await state.set_state(Form.pet_type)
        return

    if len(message.text) > 50:
        await message.answer("Имя слишком длинное (макс. 50 символов)")
        return

    await state.update_data(pet_name=message.text)
    data = await state.get_data()
    await message.answer(
        "🔍 Выберите породу:",
        reply_markup=get_breeds_keyboard(data["pet_type"].value)
    )
    await state.set_state(Form.pet_breed)

@router.message(Form.pet_breed)
async def process_pet_breed(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text == "🔙 Назад":
        await message.answer(
            "✏️ Введите имя питомца:",
            reply_markup=get_back_button()
        )
        await state.set_state(Form.pet_name)
        return

    data = await state.get_data()
    valid_breeds = {
        "кошка": ["Британская", "Сиамская", "Мейн-кун"],
        "собака": ["Лабрадор", "Овчарка", "Бульдог"]
    }.get(data["pet_type"].value, [])

    if message.text not in valid_breeds and message.text != "Другая порода":
        await message.answer("Пожалуйста, выберите породу из предложенных")
        return

    breed = None if message.text == "Другая порода" else message.text
    await state.update_data(pet_breed=breed)
    await message.answer(
        "📅 Введите дату последней вакцинации (ДД.ММ.ГГГГ) или 'нет', если не вакцинирован:",
        reply_markup=get_back_button()
    )
    await state.set_state(Form.vaccination_date)

@router.message(Form.vaccination_date)
async def process_vaccination_date(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text.lower() == "нет":
        await state.update_data(vaccination_date=None)
        data = await state.get_data()
        await save_pet(message, state, data)
        return

    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', message.text):
        await message.answer("❌ Неверный формат. Введите ДД.ММ.ГГГГ или 'нет'")
        return

    try:
        day, month, year = map(int, message.text.split('.'))
        input_date = datetime(year, month, day).date()
        today = datetime.now().date()

        if input_date > today:
            await message.answer("❌ Дата не может быть в будущем. Введите корректную дату.")
            return

        one_year_ago = today - relativedelta(years=1)

        if input_date < one_year_ago:
            await state.update_data(
                old_vaccination_date=message.text,
                vaccination_date=None
            )
            await message.answer(
                "⚠️ Эта дата больше года назад. Вакцинация делается раз в год.\n"
                "Хотите указать сегодняшнюю дату вакцинации?",
                reply_markup=get_yes_no_vaccination_keyboard()
            )
            return

        await state.update_data(vaccination_date=message.text)
        await message.answer(
            "Хотите установить напоминание о следующей вакцинации через год?",
            reply_markup=get_yes_no_vaccination_keyboard()
        )
        await state.set_state(Form.confirm_notification)

    except ValueError:
        await message.answer("❌ Некорректная дата. Введите ДД.ММ.ГГГГ")

@router.callback_query(F.data.in_(["yes_vaccination", "no_vaccination"]))
async def handle_vaccination_choice(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_state = await state.get_state()

    try:
        if current_state == Form.confirm_notification.state:
            # Обычное подтверждение напоминания
            vaccination_date = data["vaccination_date"]
            set_reminder = query.data == "yes_vaccination"
        else:
            # Обработка случая с устаревшей датой
            if query.data == "yes_vaccination":
                vaccination_date = datetime.now().strftime("%d.%m.%Y")
                set_reminder = True
            else:
                vaccination_date = data.get("old_vaccination_date")
                set_reminder = False

        with Session() as session:
            user = session.query(User).filter_by(telegram_id=query.from_user.id).first()
            if not user:
                user = User(telegram_id=query.from_user.id)
                session.add(user)
                session.commit()

            pet = Pet(
                name=data["pet_name"],
                breed=data["pet_breed"],
                pet_type=data["pet_type"],
                vaccination_date=vaccination_date,
                owner=user
            )
            session.add(pet)
            session.commit()

            if set_reminder and vaccination_date:
                try:
                    await schedule_vaccination_reminder(
                        query.bot, pet.id, user.telegram_id,
                        pet.name, vaccination_date
                    )
                    await query.message.answer(
                        f"✅ Питомец {pet.name} добавлен!\n"
                        f"Дата вакцинации: {vaccination_date}\n"
                        f"Напоминание установлено",
                        reply_markup=get_main_menu()
                    )
                except Exception as e:
                    logger.error(f"Ошибка напоминания: {e}")
                    await query.message.answer(
                        f"✅ Питомец {pet.name} добавлен!\n"
                        f"Дата вакцинации: {vaccination_date}\n"
                        "Но напоминание не установлено из-за ошибки",
                        reply_markup=get_main_menu()
                    )
            else:
                await query.message.answer(
                    f"✅ Питомец {data['pet_name']} добавлен!\n"
                    f"Дата вакцинации: {vaccination_date if vaccination_date else 'не указана'}",
                    reply_markup=get_main_menu()
                )

        await state.clear()
        await query.answer()

    except Exception as e:
        logger.error(f"Ошибка в handle_vaccination_choice: {e}")
        await query.message.answer(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_menu()
        )
        await state.clear()

async def save_pet(message: types.Message, state: FSMContext, data: dict):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            session.commit()

        pet = Pet(
            name=data["pet_name"],
            breed=data["pet_breed"],
            pet_type=data["pet_type"],
            vaccination_date=data["vaccination_date"],
            owner=user
        )
        session.add(pet)
        session.commit()

    await message.answer(
        f"✅ Питомец {data['pet_name']} успешно добавлен!",
        reply_markup=get_main_menu()
    )
    await state.clear()

@router.callback_query(F.data.startswith("edit_vacc_"))
async def edit_vaccination_start(query: CallbackQuery, state: FSMContext):
    pet_id = int(query.data.split("_")[2])
    await state.update_data(pet_id=pet_id)
    await query.message.answer(
        "📅 Введите новую дату вакцинации (ДД.ММ.ГГГГ) или 'нет' для удаления:",
        reply_markup=get_back_button()
    )
    await state.set_state(Form.edit_vaccination_date)
    await query.answer()

@router.message(Form.edit_vaccination_date)
async def process_edit_vaccination(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text.lower() == "нет":
        data = await state.get_data()
        with Session() as session:
            pet = session.query(Pet).filter_by(id=data["pet_id"]).first()
            if pet:
                pet.vaccination_date = None
                session.commit()
                for job in scheduler.get_jobs():
                    if job.id.startswith(f"vacc_{pet.id}_"):
                        scheduler.remove_job(job.id)
                await message.answer(
                    f"✅ Дата вакцинации для {pet.name} удалена",
                    reply_markup=get_main_menu()
                )
        await state.clear()
        return

    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', message.text):
        await message.answer("❌ Неверный формат. Введите ДД.ММ.ГГГГ или 'нет'")
        return

    try:
        day, month, year = map(int, message.text.split('.'))
        input_date = datetime(year, month, day).date()
        today = datetime.now().date()

        if input_date > today:
            await message.answer("❌ Дата не может быть в будущем. Введите корректную дату.")
            return

        one_year_ago = today - relativedelta(years=1)
        if input_date < one_year_ago:
            await message.answer(
                "⚠️ Эта дата больше года назад. Вакцинация делается раз в год.\n"
                "Хотите указать сегодняшнюю дату?",
                reply_markup=get_yes_no_vaccination_keyboard()
            )
            await state.update_data(old_date=message.text)
            return

        next_year_date = input_date + relativedelta(years=1)
        if next_year_date <= today:
            await message.answer(
                "⚠️ Дата вакцинации через год уже прошла.\n"
                "Хотите установить напоминание на сегодня?",
                reply_markup=get_yes_no_vaccination_keyboard()
            )
            await state.update_data(vaccination_date=message.text)
            return

        await save_vaccination_date(message, state, message.text)

    except ValueError:
        await message.answer("❌ Некорректная дата. Введите ДД.ММ.ГГГГ")

async def save_vaccination_date(message: types.Message, state: FSMContext, new_date: str):
    data = await state.get_data()
    with Session() as session:
        pet = session.query(Pet).filter_by(id=data["pet_id"]).first()
        if pet:
            old_date = pet.vaccination_date
            pet.vaccination_date = new_date
            session.commit()

            try:
                for job in scheduler.get_jobs():
                    if job.id.startswith(f"vacc_{pet.id}_"):
                        scheduler.remove_job(job.id)

                await schedule_vaccination_reminder(
                    message.bot, pet.id, pet.owner.telegram_id, pet.name, new_date
                )

                response = f"✅ Дата вакцинации для {pet.name} изменена"
                if old_date:
                    response += f":\nБыло: {old_date}\nСтало: {new_date}"
                else:
                    response += f"\nСтало: {new_date}"

                await message.answer(response, reply_markup=get_main_menu())

            except Exception as e:
                logger.error(f"Ошибка при обновлении напоминания: {e}")
                await message.answer("❌ Ошибка при обновлении напоминания", reply_markup=get_main_menu())
        else:
            await message.answer("Питомец не найден")
    await state.clear()

@router.message(F.text == "📚 Справка")
async def info_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите тип питомца:",
        reply_markup=get_info_pet_type_keyboard()
    )
    await state.set_state(Form.info_pet_type)


@router.message(Form.info_pet_type)
async def info_pet_type_selected(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text not in ["🐱 Кошка", "🐶 Собака", "🔙 Назад"]:
        await message.answer("Пожалуйста, выберите тип из предложенных")
        return

    if message.text == "🔙 Назад":
        await message.answer(
            "Главное меню",
            reply_markup=get_main_menu()
        )
        await state.clear()

    await state.update_data(info_pet_type=message.text)
    await message.answer(
        "Выберите категорию информации:",
        reply_markup=get_info_category_keyboard()
    )
    await state.set_state(Form.info_category)


@router.message(Form.info_category)
async def info_category_selected(message: types.Message, state: FSMContext):
    categories = ["🍽 Уход", "🎾 Игры", "💊 Здоровье", "🔙 Назад"]
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text not in categories:
        await message.answer("Пожалуйста, выберите категорию из предложенных")
        return

    if message.text == "🔙 Назад":
        await info_start(message, state)
        return

    data = await state.get_data()
    pet_type = data["info_pet_type"]

    info_texts = {
        "🐱 Кошка": {
            "🍽 Уход": (
                "🐱 <b>Уход за кошкой:</b>\n"
                "• Кормление: 2-3 раза в день качественным кормом\n"
                "• Вода: должна быть свежей\n"
                "• Лоток: чистите ежедневно\n"
                "• Шерсть: вычесывайте 1-2 раза в неделю\n"
                "• Когти: подстригайте по необходимости"
            ),
            "🎾 Игры": (
                "🐱 <b>Игры с кошкой:</b>\n"
                "• Играйте 15-20 минут в день\n"
                "• Используйте интерактивные игрушки\n"
                "• Обеспечьте когтеточку\n"
                "• Меняйте игрушки регулярно"
            ),
            "💊 Здоровье": (
                "🐱 <b>Здоровье кошки:</b>\n"
                "• Ежегодные прививки\n"
                "• Обработка от паразитов\n"
                "• Стерилизация/кастрация по рекомендации врача\n"
                "• Регулярные осмотры у ветеринара"
            )
        },
        "🐶 Собака": {
            "🍽 Уход": (
                "🐶 <b>Уход за собакой:</b>\n"
                "• Кормление: 2 раза в день по режиму\n"
                "• Прогулки: минимум 2-3 раза в день\n"
                "• Купание: 1 раз в месяц или по необходимости\n"
                "• Шерсть: регулярное вычесывание"
            ),
            "🎾 Игры": (
                "🐶 <b>Игры с собакой:</b>\n"
                "• Активные игры на улице\n"
                "• Тренировки и обучение командам\n"
                "• Игрушки для жевания\n"
                "• Социализация с другими собаками"
            ),
            "💊 Здоровье": (
                "🐶 <b>Здоровье собаки:</b>\n"
                "• Ежегодные прививки\n"
                "• Обработка от паразитов каждый месяц\n"
                "• Стерилизация/кастрация по рекомендации\n"
                "• Регулярные осмотры у ветеринара"
            )
        }
    }

    await message.answer(
        info_texts[pet_type][message.text],
        reply_markup=get_info_category_keyboard()
    )


@router.message(F.text == "⏰ Напоминания")
async def reminders_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⏰ Управление напоминаниями:",
        reply_markup=get_reminder_options()
    )


@router.message(F.text == "Добавить напоминание")
async def add_reminder_start(message: types.Message, state: FSMContext):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.pets:
            await message.answer("Сначала добавьте питомца", reply_markup=get_main_menu())
            return

        pets_buttons = [[KeyboardButton(text=pet.name)] for pet in user.pets]
        pets_buttons.append([KeyboardButton(text="🔙 Главное меню")])

        await message.answer(
            "Выберите питомца:",
            reply_markup=ReplyKeyboardMarkup(keyboard=pets_buttons, resize_keyboard=True)
        )
        await state.set_state(Form.reminder_pet)


@router.message(Form.reminder_pet)
async def select_pet_for_reminder(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text == "🔙 Назад":
        await reminders_menu(message, state)
        return

    with Session() as session:
        pet = session.query(Pet).filter_by(name=message.text).first()
        if not pet:
            await message.answer("Питомец не найден")
            return

        await state.update_data(pet_id=pet.id, pet_name=pet.name)
        await message.answer(
            "⏱ Введите время (ЧЧ:ММ):",
            reply_markup=get_back_button()
        )
        await state.set_state(Form.reminder_time)


@router.message(Form.reminder_time)
async def set_reminder_time(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text == "🔙 Назад":
        await add_reminder_start(message, state)
        return

    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', message.text):
        await message.answer("❌ Неверный формат. Введите ЧЧ:ММ")
        return

    await state.update_data(reminder_time=message.text)
    await message.answer(
        "📅 Выберите дни:",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(Form.reminder_days)


@router.message(Form.reminder_days)
async def set_reminder_days(message: types.Message, state: FSMContext):
    days_map = {
        "Пн": "mon", "Вт": "tue", "Ср": "wed",
        "Чт": "thu", "Пт": "fri", "Сб": "sat", "Вс": "sun",
        "Ежедневно": "daily"
    }
    selected_day = days_map.get(message.text)

    if not selected_day:
        await message.answer("Пожалуйста, выберите день из списка")
        return

    data = await state.get_data()
    with Session() as session:
        pet = session.query(Pet).filter_by(id=data["pet_id"]).first()
        reminder = Reminder(
            time=data["reminder_time"],
            days=selected_day,
            pet=pet
        )
        session.add(reminder)
        session.commit()

        try:
            await schedule_jobs(message.bot)
            await message.answer(
                f"✅ Напоминание для {pet.name} установлено!",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"Ошибка при установке напоминания: {e}")
            await message.answer(
                "❌ Ошибка при установке напоминания",
                reply_markup=get_main_menu()
            )

    await state.clear()


@router.message(F.text == "Мои напоминания")
async def show_reminders(message: types.Message):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.pets:
            await message.answer("У вас нет напоминаний", reply_markup=get_main_menu())
            return

        has_reminders = False
        await message.answer("🔔 Ваши текущие напоминания:")

        for pet in user.pets:
            if pet.reminders:
                has_reminders = True
                for reminder in pet.reminders:
                    days = "ежедневно" if reminder.days == "daily" else ", ".join(reminder.days.split(", "))
                    await message.answer(
                        f"🐾 {pet.name} в {reminder.time} ({days})",
                        reply_markup=get_reminder_actions_keyboard(reminder.id)
                    )

        if not has_reminders:
            await message.answer("У вас пока нет активных напоминаний")


@router.callback_query(F.data.startswith("edit_time_"))
async def edit_reminder_time_handler(query: CallbackQuery, state: FSMContext):
    reminder_id = int(query.data.split("_")[2])
    await state.update_data(reminder_id=reminder_id)
    await query.message.answer(
        "Введите новое время (ЧЧ:ММ):",
        reply_markup=get_back_button()
    )
    await state.set_state(Form.edit_reminder_time)
    await query.answer()


@router.message(Form.edit_reminder_time)
async def process_edit_time(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await back_to_main_menu(message, state)
        return

    if message.text == "🔙 Назад":
        await state.clear()
        await show_reminders(message)
        return

    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', message.text):
        await message.answer("❌ Неверный формат. Введите ЧЧ:ММ")
        return

    data = await state.get_data()
    with Session() as session:
        reminder = session.query(Reminder).filter_by(id=data["reminder_id"]).first()
        if reminder:
            reminder.time = message.text
            session.commit()
            try:
                await schedule_jobs(message.bot)
                await message.answer("✅ Время напоминания обновлено!", reply_markup=get_main_menu())
            except Exception as e:
                logger.error(f"Ошибка обновления времени: {e}")
                await message.answer("❌ Ошибка при обновлении", reply_markup=get_main_menu())
        else:
            await message.answer("Напоминание не найдено")
    await state.clear()


@router.callback_query(F.data.startswith("edit_days_"))
async def edit_reminder_days_handler(query: CallbackQuery, state: FSMContext):
    reminder_id = int(query.data.split("_")[2])
    await state.update_data(reminder_id=reminder_id)
    await query.message.answer(
        "📅 Выберите новые дни:",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(Form.edit_reminder_days)
    await query.answer()


@router.message(Form.edit_reminder_days)
async def process_edit_days(message: types.Message, state: FSMContext):
    days_map = {
        "Пн": "mon", "Вт": "tue", "Ср": "wed",
        "Чт": "thu", "Пт": "fri", "Сб": "sat", "Вс": "sun",
        "Ежедневно": "daily"
    }
    selected_day = days_map.get(message.text)

    if not selected_day:
        await message.answer("Пожалуйста, выберите день из списка")
        return

    data = await state.get_data()
    with Session() as session:
        reminder = session.query(Reminder).filter_by(id=data["reminder_id"]).first()
        if reminder:
            reminder.days = selected_day
            session.commit()
            try:
                await schedule_jobs(message.bot)
                await message.answer("✅ Дни напоминания обновлены!", reply_markup=get_main_menu())
            except Exception as e:
                logger.error(f"Ошибка обновления дней: {e}")
                await message.answer("❌ Ошибка при обновлении", reply_markup=get_main_menu())
        else:
            await message.answer("Напоминание не найдено")
    await state.clear()


@router.callback_query(F.data.startswith("delete_reminder_"))
async def delete_reminder_handler(query: CallbackQuery):
    reminder_id = int(query.data.split("_")[2])
    with Session() as session:
        reminder = session.query(Reminder).filter_by(id=reminder_id).first()
        if reminder:
            pet_name = reminder.pet.name
            session.delete(reminder)
            session.commit()
            remove_reminder(reminder_id)
            await query.message.edit_text(
                f"✅ Напоминание для {pet_name} удалено",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Вернуться к списку", callback_data="back_to_reminders")]
                ])
            )
            await query.answer("Напоминание удалено")
        else:
            await query.answer("Напоминание не найдено")


@router.callback_query(F.data == "back_to_reminders")
async def back_to_reminders_handler(query: CallbackQuery):
    await query.message.delete()
    await show_reminders(query.message)
    await query.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text("Действие отменено", reply_markup=get_main_menu())
    await query.answer()


def register_handlers(dp: Dispatcher, bot: Bot):
    dp.include_router(router)