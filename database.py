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

# ====== ДОБАВЬ ЭТО В КОНЕЦ ФАЙЛА database.py ======

def get_session():
    """Создает и возвращает новую сессию базы данных"""
    engine = create_engine('sqlite:///bot_orders.db', echo=False)
    Session = sessionmaker(bind=engine)
    return Session()

def get_or_create_user(session, telegram_id, username=None, first_name=None, last_name=None, referral_code=None):
    """Получает или создает пользователя"""
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        session.commit()
    
    return user

def create_order(session, user_id, bot_type, functionality, target_audience, preferences, budget=100000, partner_id=None):
    """Создает новый заказ"""
    user = session.query(User).filter_by(id=user_id).first()
    
    # Определяем процент партнера
    partner_percent = 0
    if user.referral_id and not session.query(Order).filter_by(user_id=user_id).first():
        partner_id = user.referral_id
        partner = session.query(User).filter_by(id=partner_id).first()
        
        # Считаем рефералов
        referral_count = session.query(User).filter_by(referral_id=partner_id).count()
        
        # Определяем процент
        if referral_count >= 3:
            partner_percent = 20.0
        else:
            partner_percent = 10.0
    
    order = Order(
        user_id=user_id,
        partner_id=partner_id,
        bot_type=bot_type,
        functionality=functionality,
        target_audience=target_audience,
        preferences=preferences,
        amount=budget,
        partner_percent=partner_percent
    )
    
    session.add(order)
    session.commit()
    
    return order


def get_user_orders(session, user_id):
    """Получает все заказы пользователя"""
    return session.query(Order).filter_by(user_id=user_id).all()


def get_all_orders(session):
    """Получает все заказы"""
    return session.query(Order).order_by(Order.created_at.desc()).all()


def get_partners(session):
    """Получает всех партнеров"""
    return session.query(User).filter_by(is_partner=True).all()


def update_order_status(session, order_id, status):
    """Обновляет статус заказа"""
    order = session.query(Order).filter_by(id=order_id).first()
    if order:
        order.status = status
        session.commit()
        return True
    return False


def get_partner_stats(session, partner_id):
    """Статистика партнера"""
    stats = {
        'total_referrals': session.query(User).filter_by(referral_id=partner_id).count(),
        'completed_orders': session.query(Order).filter_by(partner_id=partner_id, status='completed').count(),
        'total_earnings': 0,
        'pending_payments': 0
    }
    return stats


