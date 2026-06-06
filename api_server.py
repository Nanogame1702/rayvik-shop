from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import secrets

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с WebApp

# Секретный ключ для безопасности (замени на свой!)
API_SECRET = "your-secret-key-12345"

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Проверка API ключа
def verify_api_key(request):
    api_key = request.headers.get('X-API-Key')
    return api_key == API_SECRET

@app.route('/api/check_promo', methods=['POST'])
def check_promo():
    # Проверяем API ключ (опционально, но рекомендуется)
    if not verify_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    promo_code = data.get('code', '').strip().upper()
    user_id = data.get('user_id')
    
    if not promo_code:
        return jsonify({
            'valid': False, 
            'message': 'Введите промокод'
        })
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем промокод
    cursor.execute("""
        SELECT * FROM promocodes 
        WHERE code = ? AND active = 1
    """, (promo_code,))
    
    promo = cursor.fetchone()
    
    if not promo:
        conn.close()
        return jsonify({
            'valid': False, 
            'message': 'Неверный промокод'
        })
    
    # Проверяем срок действия
    if promo['valid_until']:
        valid_until = datetime.fromisoformat(promo['valid_until'])
        if datetime.now() > valid_until:
            conn.close()
            return jsonify({
                'valid': False, 
                'message': 'Промокод истек'
            })
    
    # Проверяем лимит использований
    if promo['max_uses'] > 0 and promo['current_uses'] >= promo['max_uses']:
        conn.close()
        return jsonify({
            'valid': False, 
            'message': 'Промокод исчерпан'
        })
    
    # Проверяем, использовал ли пользователь этот промокод
    cursor.execute("""
        SELECT COUNT(*) as count FROM promo_usage 
        WHERE user_id = ? AND code = ?
    """, (user_id, promo_code))
    
    usage = cursor.fetchone()
    if usage['count'] > 0:
        conn.close()
        return jsonify({
            'valid': False, 
            'message': 'Вы уже использовали этот промокод'
        })
    
    conn.close()
    
    # Промокод валидный!
    return jsonify({
        'valid': True, 
        'code': promo_code,
        'discount': promo['discount'],
        'type': promo['type'],
        'message': f'Промокод активирован! Скидка {promo["discount"]}%'
    })

@app.route('/api/apply_promo', methods=['POST'])
def apply_promo():
    """Фиксируем использование промокода после покупки"""
    if not verify_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    promo_code = data.get('code', '').upper()
    user_id = data.get('user_id')
    username = data.get('username', '')
    discount_amount = data.get('discount_amount', 0)
    order_id = data.get('order_id', '')
    product_name = data.get('product_name', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Добавляем запись об использовании
    cursor.execute("""
        INSERT INTO promo_usage 
        (user_id, username, code, discount_amount, order_id, product_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, promo_code, discount_amount, order_id, product_name))
    
    # Увеличиваем счетчик использований
    cursor.execute("""
        UPDATE promocodes 
        SET current_uses = current_uses + 1
        WHERE code = ?
    """, (promo_code,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/promo_stats', methods=['GET'])
def promo_stats():
    """Статистика по промокодам (для админа)"""
    if not verify_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем все промокоды
    cursor.execute("""
        SELECT 
            code, 
            discount, 
            max_uses, 
            current_uses, 
            active,
            description,
            created_at
        FROM promocodes
        ORDER BY created_at DESC
    """)
    
    promos = []
    for row in cursor.fetchall():
        promos.append({
            'code': row['code'],
            'discount': row['discount'],
            'max_uses': row['max_uses'],
            'current_uses': row['current_uses'],
            'active': bool(row['active']),
            'description': row['description'],
            'created_at': row['created_at']
        })
    
    conn.close()
    
    return jsonify({'promocodes': promos})

@app.route('/health', methods=['GET'])
def health():
    """Проверка работы API"""
    return jsonify({'status': 'ok', 'message': 'API is running'})

if __name__ == '__main__':
    print("🚀 API сервер запущен на http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
