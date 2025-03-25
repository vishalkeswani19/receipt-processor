import os
from flask import Flask, request, jsonify
import uuid
import re
import math
from datetime import datetime
import sqlite3
import logging
from threading import Lock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from environment variables
PORT = int(os.getenv('PORT', 8080))
DB_PATH = os.getenv('DB_PATH', 'receipts.db')

# Thread-safe database access
db_lock = Lock()

# Initialize SQLite database
def init_db():
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY,
                retailer TEXT,
                purchase_date TEXT,
                purchase_time TEXT,
                items TEXT,
                total REAL,
                points INTEGER
            )
        ''')
        conn.commit()

class Item:
    def __init__(self, short_description, price):
        self.short_description = short_description
        try:
            self.price = float(price)
            if self.price < 0:
                raise ValueError("Price cannot be negative")
        except ValueError as e:
            raise ValueError(f"Invalid price '{price}': {str(e)}")

@app.route('/')
def home():
    return jsonify({
        'message': 'Welcome to Receipt Processor. Use /receipts/process to submit a receipt or /receipts/<id>/points to get points.'
    }), 200

@app.route('/receipts/process', methods=['POST'])
def process_receipt():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        # Validate required fields
        required_fields = ['retailer', 'purchaseDate', 'purchaseTime', 'items', 'total']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Additional validation
        if not isinstance(data['items'], list):
            return jsonify({'error': 'Items must be a list'}), 400
        if not data['retailer'].strip():
            return jsonify({'error': 'Retailer cannot be empty'}), 400

        # Parse items
        items = []
        for item in data['items']:
            if not all(k in item for k in ['shortDescription', 'price']):
                return jsonify({'error': 'Each item must have shortDescription and price'}), 400
            items.append(Item(item['shortDescription'], item['price']))

        total = float(data['total'])
        if total < 0:
            return jsonify({'error': 'Total cannot be negative'}), 400

        # Create receipt
        receipt_id = str(uuid.uuid4())
        points = calculate_points(data['retailer'], data['purchaseDate'], data['purchaseTime'], items, total)

        # Store in database
        with db_lock, sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                'INSERT INTO receipts (id, retailer, purchase_date, purchase_time, items, total, points) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (receipt_id, data['retailer'], data['purchaseDate'], data['purchaseTime'], str([vars(item) for item in items]), total, points)
            )
            conn.commit()

        logger.info(f"Processed receipt {receipt_id} with {points} points")
        return jsonify({'id': receipt_id}), 200

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/receipts/<id>/points', methods=['GET'])
def get_points(id):
    try:
        with db_lock, sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT points FROM receipts WHERE id = ?', (id,))
            result = cursor.fetchone()
            if result is None:
                return jsonify({'error': 'Receipt not found'}), 404
            points = result[0]
        
        logger.info(f"Retrieved points for receipt {id}: {points}")
        return jsonify({'points': points}), 200

    except Exception as e:
        logger.error(f"Error retrieving points for {id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def calculate_points(retailer, purchase_date, purchase_time, items, total):
    points = 0

    # Rule 1: One point for every alphanumeric character in the retailer name
    points += len(re.sub(r'[^a-zA-Z0-9]', '', retailer))

    # Rule 2: 50 points if the total is a round dollar amount with no cents
    if total == math.floor(total):
        points += 50

    # Rule 3: 25 points if the total is a multiple of 0.25
    if math.fmod(total * 100, 25) == 0:
        points += 25

    # Rule 4: 5 points for every two items on the receipt
    points += (len(items) // 2) * 5

    # Rule 5: Points based on item description length (multiple of 3)
    for item in items:
        trimmed_desc = item.short_description.strip()
        if len(trimmed_desc) > 0 and len(trimmed_desc) % 3 == 0:
            points += math.ceil(item.price * 0.2)

    # Rule 6: 5 points if the total is greater than 10.00
    if total > 10.00:
        points += 5

    # Rule 7: 6 points if the day in the purchase date is odd
    try:
        date = datetime.strptime(purchase_date, '%Y-%m-%d')
        if date.day % 2 != 0:
            points += 6
    except ValueError:
        logger.warning(f"Invalid purchase date: {purchase_date}")

    # Rule 8: 10 points if the time of purchase is after 2:00pm and before 4:00pm
    try:
        purchase_time_dt = datetime.strptime(purchase_time, '%H:%M')
        start_time = datetime.strptime('14:00', '%H:%M')
        end_time = datetime.strptime('16:00', '%H:%M')
        if start_time < purchase_time_dt < end_time:
            points += 10
    except ValueError:
        logger.warning(f"Invalid purchase time: {purchase_time}")

    return points

if __name__ == '__main__':
    init_db()
    logger.info(f"Starting server on port {PORT}...")
    try:
        from gunicorn.app.base import BaseApplication

        class StandaloneApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            'bind': f'0.0.0.0:{PORT}',
            'workers': 4,
            'timeout': 30,
        }
        StandaloneApplication(app, options).run()
    except ImportError:
        logger.warning("Gunicorn not found, falling back to Flask development server")
        app.run(host='0.0.0.0', port=PORT, debug=False)