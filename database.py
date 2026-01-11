from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Определяем DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot_orders.db')

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    referral_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    join_date = Column(DateTime, default=datetime.now)
    is_partner = Column(Boolean, default=False)

    # Отношения
    referrals = relationship('User', backref='referrer', remote_side=[id])
    orders_as_client = relationship('Order', back_populates='user', foreign_keys='Order.user_id')
    orders_as_partner = relationship('Order', back_populates='partner', foreign_keys='Order.partner_id')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    partner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    bot_type = Column(String(100))
    functionality = Column(Text)
    target_audience = Column(Text)
    preferences = Column(Text)
    status = Column(String(50), default='new')
    created_at = Column(DateTime, default=datetime.now)
    partner_paid = Column(Boolean, default=False)
    partner_percent = Column(Float, default=10.0)
    amount = Column(Float, default=100000.0)

    user = relationship('User', back_populates='orders_as_client', foreign_keys=[user_id])
    partner = relationship('User', back_populates='orders_as_partner', foreign_keys=[partner_id])
    payments = relationship('PartnerPayment', back_populates='order', foreign_keys='PartnerPayment.order_id')


class PartnerPayment(Base):
    __tablename__ = 'partner_payments'

    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    amount = Column(Float, nullable=False)
    percent = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.now)
    paid = Column(Boolean, default=False)

    partner = relationship('User', back_populates='partner_payments', foreign_keys=[partner_id])
    order = relationship('Order', back_populates='payments', foreign_keys=[order_id])


def init_db():
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    Session = sessionmaker(bind=engine)

    return Session()


