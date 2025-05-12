from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from enum import Enum as PyEnum
from datetime import datetime
import pytz

class PetType(PyEnum):
    CAT = "кошка"
    DOG = "собака"

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    pets = relationship("Pet", back_populates="owner")

class Pet(Base):
    __tablename__ = 'pets'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    breed = Column(String, nullable=True)
    pet_type = Column(Enum(PetType))
    vaccination_date = Column(String)
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship("User", back_populates="pets")
    reminders = relationship("Reminder", back_populates="pet")

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    time = Column(String)
    days = Column(String)
    pet_id = Column(Integer, ForeignKey('pets.id'))
    pet = relationship("Pet", back_populates="reminders")
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Europe/Moscow')))

engine = create_engine('sqlite:///pets.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)