from flask import Flask, render_template, jsonify, request
from sqlalchemy.orm import sessionmaker
from database import init_db, User, Order, PartnerPayment
from config import CURRENCY
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'telegram-bot-admin-panel-secret-key'

# Инициализация базы
engine = init_db()
Session = sessionmaker(bind=engine)


def get_db_session():
    return Session()


@app.route('/')
def admin_dashboard():
    session = get_db_session()
    try:
        # Статистика
        total_orders = session.query(Order).count()
        new_orders = session.query(Order).filter_by(status='new').count()
        total_partners = session.query(User).filter_by(is_partner=True).count()

        # Выплаты
        pending_payments = session.query(PartnerPayment).filter_by(paid=False).all()
        pending_sum = sum(p.amount for p in pending_payments)

        # Последние заказы (5 штук)
        orders = session.query(Order).order_by(Order.created_at.desc()).limit(5).all()

        # Собираем данные для заказов
        order_list = []
        for order in orders:
            user = session.query(User).filter_by(id=order.user_id).first()
            partner = session.query(User).filter_by(id=order.partner_id).first() if order.partner_id else None

            order_list.append({
                'id': order.id,
                'user': {
                    'name': f"{user.first_name} {user.last_name or ''}",
                    'username': user.username
                } if user else {'name': 'Неизвестно', 'username': ''},
                'bot_type': order.bot_type,
                'status': order.status,
                'amount': order.amount,
                'created_at': order.created_at,
                'partner': {
                    'name': f"{partner.first_name} {partner.last_name or ''}",
                    'username': partner.username
                } if partner else None
            })

        # Партнёры
        partners = session.query(User).filter_by(is_partner=True).all()
        partner_stats = []
        for partner in partners:
            referrals = session.query(User).filter_by(referral_id=partner.id).count()
            payments = session.query(PartnerPayment).filter_by(partner_id=partner.id).all()
            pending = sum(p.amount for p in payments if not p.paid)
            earned = sum(p.amount for p in payments if p.paid)

            partner_stats.append({
                'id': partner.id,
                'name': f"{partner.first_name} {partner.last_name or ''}",
                'username': partner.username,
                'referrals': referrals,
                'pending_payments': pending,
                'total_earnings': earned
            })

        return render_template('admin.html',
                               stats={
                                   'total_orders': total_orders,
                                   'new_orders': new_orders,
                                   'total_partners': total_partners,
                                   'pending_payments': pending_sum
                               },
                               orders=order_list,
                               partners=partner_stats,
                               currency=CURRENCY)
    except Exception as e:
        print(f"Ошибка в админ-панели: {e}")
        return f"Ошибка сервера: {e}", 500
    finally:
        session.close()


@app.route('/orders')
def orders_page():
    session = get_db_session()
    try:
        status = request.args.get('status', 'all')
        partner_id = request.args.get('partner', 'all')

        # Базовый запрос
        query = session.query(Order)

        # Фильтры
        if status != 'all':
            query = query.filter_by(status=status)

        if partner_id != 'all':
            query = query.filter_by(partner_id=partner_id)

        orders = query.order_by(Order.created_at.desc()).all()

        # Собираем данные
        order_list = []
        for order in orders:
            user = session.query(User).filter_by(id=order.user_id).first()
            partner = session.query(User).filter_by(id=order.partner_id).first() if order.partner_id else None

            order_list.append({
                'order': order,
                'user': user,
                'partner': partner
            })

        # Партнёры для фильтра
        partners = session.query(User).filter_by(is_partner=True).all()

        return render_template('orders.html',
                               orders=order_list,
                               partners=partners,
                               current_status=status,
                               current_partner=partner_id,
                               currency=CURRENCY)
    finally:
        session.close()


@app.route('/api/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    session = get_db_session()
    try:
        data = request.json
        order = session.query(Order).filter_by(id=order_id).first()
        if order:
            order.status = data.get('status', order.status)
            session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/pay_partner/<int:payment_id>', methods=['POST'])
def pay_partner(payment_id):
    session = get_db_session()
    try:
        payment = session.query(PartnerPayment).filter_by(id=payment_id).first()
        if payment:
            payment.paid = True
            payment.payment_date = datetime.now()

            # Обновляем заказ
            order = session.query(Order).filter_by(id=payment.order_id).first()
            if order:
                order.partner_paid = True

            session.commit()
            return jsonify({
                'success': True,
                'message': f'Выплачено {payment.amount:.2f}{CURRENCY}'
            })
        return jsonify({'success': False}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Admin panel is running'})


