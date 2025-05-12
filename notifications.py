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
        # Удаляем старые напоминания
        for job in scheduler.get_jobs():
            if job.id.startswith(f"vacc_{pet_id}_"):
                scheduler.remove_job(job.id)

        # Если дата None - не создаем напоминание
        if vaccination_date is None:
            return

        day, month, year = map(int, vaccination_date.split('.'))
        vacc_date = datetime(year, month, day).date()
        today = datetime.now().date()

        # Если дата в будущем - ставим напоминание
        if vacc_date > today:
            run_date = vacc_date
            message = f"⏰ {pet_name} пора на ежегодную вакцинацию!"
        else:
            # Вычисляем следующую годовщину
            next_vacc_date = vacc_date + relativedelta(years=1)
            while next_vacc_date <= today:
                next_vacc_date += relativedelta(years=1)

            run_date = next_vacc_date
            message = f"⏰ {pet_name} пора на ежегодную вакцинацию!\nПоследняя запись: {vacc_date.strftime('%d.%m.%Y')}"

        scheduler.add_job(
            send_notification,
            'date',
            run_date=run_date,
            args=[bot, chat_id, message],
            id=f"vacc_{pet_id}_{uuid.uuid4().hex[:4]}"
        )
    except Exception as e:
        logger.error(f"Ошибка создания напоминания: {e}")
        raise


async def schedule_jobs(bot: Bot):
    try:
        for job in scheduler.get_jobs():
            if job.id.startswith(("reminder_", "vacc_")):
                scheduler.remove_job(job.id)

        with Session() as session:
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
                        args=[bot, reminder.pet.owner.telegram_id,
                              f"⏰ Пора покормить {reminder.pet.name}!"],
                        id=f"reminder_{reminder.id}_{uuid.uuid4().hex[:4]}",
                        timezone='Europe/Moscow'
                    )
                except Exception as e:
                    logger.error(f"Ошибка напоминания {reminder.id}: {e}")

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
            if f"reminder_{reminder_id}_" in job.id or f"vacc_{reminder_id}_" in job.id:
                job.remove()
                removed = True
        return removed
    except Exception as e:
        logger.error(f"Ошибка удаления напоминания: {e}")
        return False