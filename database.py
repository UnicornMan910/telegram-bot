from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = 'sqlite:///bot_orders.db'

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    referral_id = Column(Integer, nullable=True)
    join_date = Column(DateTime, default=datetime.now)
    is_partner = Column(Boolean, default=False)

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    partner_id = Column(Integer, nullable=True)
    bot_type = Column(String(100))
    functionality = Column(Text)
    target_audience = Column(Text)
    preferences = Column(Text)
    status = Column(String(50), default='new')
    created_at = Column(DateTime, default=datetime.now)
    partner_paid = Column(Boolean, default=False)
    partner_percent = Column(Float, default=10.0)
    amount = Column(Float, default=100.0)

# УДАЛИ КЛАСС PartnerPayment полностью если не нужен
# class PartnerPayment(Base):
#     __tablename__ = 'partner_payments'
#     ...

def init_db():
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine
