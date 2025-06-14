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
        for job in scheduler.get_jobs():
            if job.id and job.id.startswith(f"vacc_{pet_id}_"):
                scheduler.remove_job(job.id)

        if not vaccination_date:
            return

        day, month, year = map(int, vaccination_date.split('.'))
        vacc_date = datetime(year, month, day).date()
        today = datetime.now().date()

        next_vacc_date = vacc_date + relativedelta(years=1)

        if next_vacc_date <= today:
            next_vacc_date = today + relativedelta(years=1)

        message = f"⏰ {pet_name}, пора на ежегодную вакцинацию!"
        job_id = f"vacc_{pet_id}_{uuid.uuid4().hex[:4]}"

        scheduler.add_job(
            send_notification,
            'date',
            run_date=datetime(
                next_vacc_date.year,
                next_vacc_date.month,
                next_vacc_date.day,
                9, 0  # В 9:00 утра
            ),
            args=[bot, chat_id, message],
            id=job_id,
            misfire_grace_time=3600
        )

        logger.info(f"Напоминание о вакцинации установлено для {pet_name} на {next_vacc_date}")
    except Exception as e:
        logger.error(f"Ошибка создания напоминания о вакцинации: {e}")
        raise


async def schedule_jobs(bot: Bot):
    try:
        for job in scheduler.get_jobs():
            if job.id and job.id.startswith(("reminder_", "vacc_")):
                scheduler.remove_job(job.id)

        with Session() as session:
            reminders = session.query(Reminder).all()
            for reminder in reminders:
                try:
                    if not reminder.pet:
                        continue

                    hour, minute = map(int, reminder.time.split(':'))
                    days = "daily" if reminder.days == "daily" else reminder.days
                    job_id = f"reminder_{reminder.id}_{uuid.uuid4().hex[:4]}"

                    scheduler.add_job(
                        send_notification,
                        'cron',
                        day_of_week=None if reminder.days == "daily" else days,
                        hour=hour,
                        minute=minute,
                        args=[bot, reminder.pet.owner.telegram_id, f"⏰ Пора покормить {reminder.pet.name}!"],
                        id=job_id,
                        timezone='Europe/Moscow',
                        misfire_grace_time=300
                    )
                except Exception as e:
                    logger.error(f"Ошибка напоминания {reminder.id}: {e}")


            pets = session.query(Pet).all()
            for pet in pets:
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
            logger.info("Планировщик задач запущен")
    except Exception as e:
        logger.error(f"Ошибка планировщика: {e}")
        raise


def remove_reminder(reminder_id: int):
    try:
        removed = False
        for job in scheduler.get_jobs():
            if job.id and (f"reminder_{reminder_id}_" in job.id or f"vacc_{reminder_id}_" in job.id):
                scheduler.remove_job(job.id)
                removed = True
        return removed
    except Exception as e:
        logger.error(f"Ошибка удаления напоминания: {e}")
        return False