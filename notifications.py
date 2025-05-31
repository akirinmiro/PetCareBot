from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import Session, Reminder, Pet
import pytz
import uuid
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def send_notification(bot: Bot, chat_id: int, message: str):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Уведомление отправлено: {message}")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")


async def schedule_vaccination_reminder(bot: Bot, pet_id: int, chat_id: int, pet_name: str, vaccination_date: str):
    try:
        # Удаляем старые напоминания для этого питомца
        for job in scheduler.get_jobs():
            if job.id.startswith(f"vacc_{pet_id}_"):
                scheduler.remove_job(job.id)

        if vaccination_date is None:
            return

        day, month, year = map(int, vaccination_date.split('.'))
        vacc_date = datetime(year, month, day).date()
        next_vacc_date = vacc_date + relativedelta(years=1)

        today = datetime.now().date()
        while next_vacc_date <= today:
            next_vacc_date += relativedelta(years=1)

        message = f"⏰ {pet_name}, пора на ежегодную вакцинацию!"

        scheduler.add_job(
            send_notification,
            'date',
            run_date=datetime(next_vacc_date.year, next_vacc_date.month, next_vacc_date.day, 9, 0),
            args=[bot, chat_id, message],
            id=f"vacc_{pet_id}_{uuid.uuid4().hex[:4]}"
        )

        logger.info(f"Напоминание о вакцинации установлено для {pet_name} на {next_vacc_date}")
    except Exception as e:
        logger.error(f"Ошибка создания напоминания о вакцинации: {e}")
        raise


async def schedule_jobs(bot: Bot):
    try:
        # Очистка старых задач
        for job in scheduler.get_jobs():
            if job.id.startswith(("reminder_", "vacc_")):
                scheduler.remove_job(job.id)

        with Session() as session:
            # Загрузка напоминаний о кормлении
            for reminder in session.query(Reminder).all():
                try:
                    hour, minute = map(int, reminder.time.split(':'))
                    days = "daily" if reminder.days == "daily" else reminder.days
                    scheduler.add_job(
                        send_notification,
                        'cron',
                        day_of_week=None if reminder.days == "daily" else days,
                        hour=hour,
                        minute=minute,
                        args=[bot, reminder.pet.owner.telegram_id, f"⏰ Пора покормить {reminder.pet.name}!"],
                        id=f"reminder_{reminder.id}_{uuid.uuid4().hex[:4]}",
                        timezone='Europe/Moscow'
                    )
                except Exception as e:
                    logger.error(f"Ошибка напоминания {reminder.id}: {e}")

            # Загрузка напоминаний о вакцинации
            for pet in session.query(Pet).all():
                if pet.vaccination_date:
                    try:
                        await schedule_vaccination_reminder(
                            bot, pet.id, pet.owner.telegram_id,
                            pet.name, pet.vaccination_date
                        )
                    except Exception as e:
                        logger.error(f"Ошибка вакцинации {pet.id}: {e}")

        if not scheduler.running:
            scheduler.start()
    except Exception as e:
        logger.error(f"Ошибка планировщика: {e}")


def remove_reminder(reminder_id: int):
    try:
        removed = False
        for job in scheduler.get_jobs():
            if job.id.startswith(f"reminder_{reminder_id}_") or job.id.startswith(f"vacc_{reminder_id}_"):
                scheduler.remove_job(job.id)
                removed = True
        return removed
    except Exception as e:
        logger.error(f"Ошибка удаления напоминания: {e}")
        return False