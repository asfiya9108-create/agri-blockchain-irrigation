from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import time
import random
import hashlib
import json
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import os

app = Flask(__name__, template_folder='../frontend', static_folder='../frontend')
app.secret_key = "agriculture_blockchain_secret_key_2026"
CORS(app)

# USERS
USERS = {
    "demo": {"password": "demo123", "farmer_id": "F001", "name": "Demo Farmer"},
    "admin": {"password": "admin123", "farmer_id": "F001", "name": "Administrator"}
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# BLOCKCHAIN
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty=2):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

class AgriBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = 2
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, [{
            "type": "genesis",
            "timestamp": time.time(),
            "data": "Genesis Block"
        }], time.time(), "0")
        self.chain.append(genesis_block)

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        transaction["timestamp"] = time.time()
        self.pending_transactions.append(transaction)
        return self.get_latest_block().index + 1

    def mine_pending_transactions(self, miner_address):
        if not self.pending_transactions:
            return
        block = Block(
            len(self.chain),
            self.pending_transactions,
            time.time(),
            self.get_latest_block().hash
        )
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

    def get_irrigation_records(self, farmer_id=None):
        records = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("type") == "irrigation":
                    if farmer_id is None or tx.get("farmer_id") == farmer_id:
                        record = tx.copy()
                        record["block_index"] = block.index
                        record["block_hash"] = block.hash
                        record["timestamp_readable"] = datetime.fromtimestamp(
                            tx.get("timestamp", 0)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                        records.append(record)
        return records

# SENSORS
class SoilMoistureSensor:
    def __init__(self, sensor_id, location):
        self.sensor_id = sensor_id
        self.location = location
        self.base_moisture = 50

    def read_moisture(self):
        variation = random.uniform(-10, 10)
        moisture = self.base_moisture + variation
        noise = random.uniform(-2, 2)
        moisture += noise
        return max(0, min(100, round(moisture, 2)))

    def get_reading(self):
        moisture = self.read_moisture()
        return {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "soil_moisture": moisture,
            "timestamp": time.time(),
            "timestamp_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

class WaterFlowSensor:
    def __init__(self, sensor_id, pipe_diameter):
        self.sensor_id = sensor_id
        self.pipe_diameter = pipe_diameter
        self.flow_rate = 0.0
        self.total_water_used = 0.0

    def measure_flow_rate(self):
        base_flow = random.uniform(1.5, 3.0)
        variation = random.uniform(-0.5, 0.5)
        self.flow_rate = round(base_flow + variation, 2)
        return self.flow_rate

    def measure_water_usage(self, duration_seconds):
        flow_rate = self.measure_flow_rate()
        usage = flow_rate * duration_seconds / 3600
        usage = round(usage, 2)
        self.total_water_used += usage
        return usage

class IrrigationController:
    def __init__(self, controller_id, water_flow_sensor):
        self.controller_id = controller_id
        self.water_flow_sensor = water_flow_sensor
        self.is_running = False

    def start_irrigation(self):
        if self.is_running:
            return {"status": "ALREADY_RUNNING", "message": "Irrigation already running"}
        self.is_running = True
        return {"status": "STARTED", "message": "Irrigation started successfully"}

    def stop_irrigation(self):
        if not self.is_running:
            return {"status": "ALREADY_STOPPED", "message": "Irrigation not running"}
        duration = 10
        water_used = self.water_flow_sensor.measure_water_usage(duration)
        self.is_running = False
        return {"status": "STOPPED", "water_used_liters": water_used, "message": "Irrigation stopped"}

    def get_status(self):
        return {
            "controller_id": self.controller_id,
            "is_running": self.is_running,
            "total_water_used": self.water_flow_sensor.total_water_used,
            "flow_rate": self.water_flow_sensor.flow_rate
        }

class SensorDataAggregator:
    def __init__(self):
        self.moisture_sensors = {}
        self.water_flow_sensors = {}
        self.controllers = {}

    def register_moisture_sensor(self, sensor_id, location):
        sensor = SoilMoistureSensor(sensor_id, location)
        self.moisture_sensors[sensor_id] = sensor
        return sensor

    def register_water_flow_sensor(self, sensor_id, pipe_diameter):
        sensor = WaterFlowSensor(sensor_id, pipe_diameter)
        self.water_flow_sensors[sensor_id] = sensor
        return sensor

    def register_controller(self, controller_id, flow_sensor_id):
        controller = IrrigationController(controller_id, self.water_flow_sensors[flow_sensor_id])
        self.controllers[controller_id] = controller
        return controller

    def get_all_sensor_data(self):
        data = {
            "moisture_sensors": {},
            "water_flow_sensors": {},
            "controllers": {},
            "timestamp": time.time()
        }
        for sensor_id, sensor in self.moisture_sensors.items():
            data["moisture_sensors"][sensor_id] = sensor.get_reading()
        for sensor_id, sensor in self.water_flow_sensors.items():
            data["water_flow_sensors"][sensor_id] = {
                "flow_rate": sensor.flow_rate,
                "total_water_used": sensor.total_water_used
            }
        for controller_id, controller in self.controllers.items():
            data["controllers"][controller_id] = controller.get_status()
        return data

# INITIALIZE
blockchain = AgriBlockchain()
sensor_aggregator = SensorDataAggregator()

sensor_aggregator.register_moisture_sensor("MS_001", "Field A - North")
sensor_aggregator.register_moisture_sensor("MS_002", "Field A - South")
sensor_aggregator.register_water_flow_sensor("WF_001", 2.5)
sensor_aggregator.register_controller("CTRL_001", "WF_001")

def evaluate_irrigation(soil_moisture, farmer_id):
    if soil_moisture < 30:
        status = "CRITICAL - Irrigation Required"
        action = "START_IRRIGATION"
    elif soil_moisture < 45:
        status = "LOW - Irrigation Recommended"
        action = "START_IRRIGATION"
    elif soil_moisture <= 65:
        status = "OPTIMAL - No Action Needed"
        action = "MAINTAIN"
    elif soil_moisture < 75:
        status = "HIGH - Monitor Closely"
        action = "STOP_IRRIGATION"
    else:
        status = "EXCESSIVE - Stop Irrigation"
        action = "STOP_IRRIGATION"
    
    transaction = {
        "type": "irrigation_decision",
        "farmer_id": farmer_id,
        "soil_moisture": soil_moisture,
        "status": status,
        "action": action,
        "timestamp": time.time()
    }
    blockchain.add_transaction(transaction)
    
    return {
        "status": status,
        "action": action,
        "recommendation": f"Soil moisture is {soil_moisture}%. {status}"
    }

# Populate sample data
sample_records = [
    {"farmer_id": "F001", "soil_moisture": 45.2, "water_usage": 120.5, "status": "COMPLETED"},
    {"farmer_id": "F001", "soil_moisture": 38.1, "water_usage": 150.3, "status": "COMPLETED"},
    {"farmer_id": "F001", "soil_moisture": 55.7, "water_usage": 95.8, "status": "COMPLETED"},
    {"farmer_id": "F001", "soil_moisture": 62.3, "water_usage": 80.2, "status": "COMPLETED"},
    {"farmer_id": "F001", "soil_moisture": 48.9, "water_usage": 110.4, "status": "COMPLETED"}
]
for record in sample_records:
    record["type"] = "irrigation"
    record["action_taken"] = "AUTO"
    blockchain.add_transaction(record)
blockchain.mine_pending_transactions("miner_address")
# ============================================================
# SOIL DETECTION MODULE
# ============================================================

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

SOIL_DATABASE = {
    "Alluvial Soil": {
        "color_ranges": {"r": (120, 200), "g": (100, 170), "b": (70, 130)},
        "crops": [
            "Rice (Paddy)", "Wheat", "Sugarcane", "Maize (Corn)",
            "Cotton", "Jute", "Pulses (Lentils, Chickpeas)",
            "Oilseeds (Mustard, Sunflower)", "Vegetables", "Fruits (Mango, Banana)"
        ],
        "description": "Fertile soil rich in potash and lime. Found in river plains and deltas.",
        "ph_range": "6.5 - 8.0",
        "best_for": "Cereals and cash crops"
    },
    "Black Soil (Regur)": {
        "color_ranges": {"r": (40, 100), "g": (35, 90), "b": (30, 80)},
        "crops": [
            "Cotton", "Soybean", "Sugarcane", "Wheat",
            "Jowar (Sorghum)", "Bajra (Pearl Millet)", "Linseed",
            "Tobacco", "Castor", "Citrus Fruits", "Vegetables"
        ],
        "description": "Rich in iron, lime, calcium, magnesium. High moisture retention.",
        "ph_range": "7.0 - 8.5",
        "best_for": "Cotton and oilseeds"
    },
    "Red Soil": {
        "color_ranges": {"r": (150, 220), "g": (80, 140), "b": (60, 110)},
        "crops": [
            "Millets", "Pulses", "Groundnut", "Tobacco",
            "Potato", "Rice", "Wheat", "Sugarcane",
            "Fruits (Mango, Orange)", "Vegetables"
        ],
        "description": "Rich in iron oxide. Low in nitrogen and phosphorus.",
        "ph_range": "5.5 - 7.0",
        "best_for": "Millets and pulses"
    },
    "Laterite Soil": {
        "color_ranges": {"r": (160, 210), "g": (90, 130), "b": (50, 90)},
        "crops": [
            "Tea", "Coffee", "Rubber", "Cashew",
            "Coconut", "Tapioca", "Fruits (Pineapple)",
            "Rice (with fertilizers)", "Sugarcane"
        ],
        "description": "Rich in iron and aluminum. Poor in nitrogen and lime.",
        "ph_range": "4.5 - 6.0",
        "best_for": "Plantation crops"
    },
    "Sandy Soil": {
        "color_ranges": {"r": (200, 245), "g": (180, 225), "b": (140, 190)},
        "crops": [
            "Watermelon", "Muskmelon", "Groundnut", "Potato",
            "Carrots", "Radish", "Cucumber", "Coconut",
            "Cashew", "Millets (with irrigation)"
        ],
        "description": "Light, warm, dry soil. Drains quickly. Low nutrients.",
        "ph_range": "5.5 - 7.0",
        "best_for": "Root vegetables and melons"
    },
    "Clay Soil": {
        "color_ranges": {"r": (70, 130), "g": (60, 115), "b": (55, 100)},
        "crops": [
            "Rice", "Wheat", "Broccoli", "Cabbage",
            "Cauliflower", "Brussels Sprouts", "Beans",
            "Corn", "Lettuce (with drainage)"
        ],
        "description": "Heavy soil that retains water. Rich in nutrients.",
        "ph_range": "6.0 - 7.5",
        "best_for": "Rice and leafy vegetables"
    },
    "Loamy Soil": {
        "color_ranges": {"r": (100, 160), "g": (80, 140), "b": (60, 110)},
        "crops": [
            "Wheat", "Rice", "Sugarcane", "Maize",
            "Cotton", "Vegetables", "Fruits",
            "Pulses", "Oilseeds", "Almost all crops"
        ],
        "description": "Ideal soil - perfect balance of sand, silt, and clay.",
        "ph_range": "6.0 - 7.0",
        "best_for": "Most crops - BEST soil type"
    },
    "Peaty Soil": {
        "color_ranges": {"r": (50, 100), "g": (40, 90), "b": (30, 70)},
        "crops": [
            "Vegetables", "Salad crops", "Blueberries",
            "Cranberries", "Rice", "Onions", "Carrots",
            "Celery", "Potatoes"
        ],
        "description": "Rich in organic matter. High moisture content.",
        "ph_range": "3.5 - 5.5",
        "best_for": "Berry crops and vegetables"
    },
    "Saline Soil": {
        "color_ranges": {"r": (190, 240), "g": (185, 235), "b": (170, 220)},
        "crops": [
            "Barley", "Sugar Beet", "Cotton (salt-tolerant varieties)",
            "Date Palm", "Quinoa", "Kale", "Asparagus",
            "Rosemary", "Salt-tolerant grasses"
        ],
        "description": "High salt content. Limited crop options.",
        "ph_range": "7.5 - 8.5",
        "best_for": "Salt-tolerant crops"
    }
}


def analyze_soil_image(image_path):
    try:
        img = Image.open(image_path).convert('RGB')
        img = img.resize((300, 300))
        img_array = np.array(img)
        center = img_array[75:225, 75:225]

        avg_r = float(np.mean(center[:, :, 0]))
        avg_g = float(np.mean(center[:, :, 1]))
        avg_b = float(np.mean(center[:, :, 2]))

        brightness = (avg_r + avg_g + avg_b) / 3

        best_match = None
        best_score = float('inf')

        for soil_name, soil_data in SOIL_DATABASE.items():
            r_min, r_max = soil_data["color_ranges"]["r"]
            g_min, g_max = soil_data["color_ranges"]["g"]
            b_min, b_max = soil_data["color_ranges"]["b"]

            r_mid = (r_min + r_max) / 2
            g_mid = (g_min + g_max) / 2
            b_mid = (b_min + b_max) / 2

            distance = (
                ((avg_r - r_mid) ** 2) +
                ((avg_g - g_mid) ** 2) +
                ((avg_b - b_mid) ** 2)
            ) ** 0.5

            if distance < best_score:
                best_score = distance
                best_match = soil_name

        confidence = max(0, min(100, round(100 - (best_score / 4), 1)))
        soil_info = SOIL_DATABASE[best_match]
        color_hex = '#{:02x}{:02x}{:02x}'.format(int(avg_r), int(avg_g), int(avg_b))

        return {
            "success": True,
            "soil_type": best_match,
            "confidence": confidence,
            "color_analysis": {
                "r": round(avg_r, 1),
                "g": round(avg_g, 1),
                "b": round(avg_b, 1),
                "hex": color_hex,
                "brightness": round(brightness, 1)
            },
            "description": soil_info["description"],
            "ph_range": soil_info["ph_range"],
            "best_for": soil_info["best_for"],
            "recommended_crops": soil_info["crops"],
            "total_crops": len(soil_info["crops"])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
# ROUTES
@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if username in USERS and USERS[username]['password'] == password:
        session['logged_in'] = True
        session['username'] = username
        session['farmer_id'] = USERS[username]['farmer_id']
        session['user_name'] = USERS[username]['name']
        return jsonify({"success": True, "message": "Login successful", "user": USERS[username]})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'logged_in' in session and session['logged_in']:
        return jsonify({"authenticated": True, "username": session.get('username'), "name": session.get('user_name')})
    return jsonify({"authenticated": False}), 401

@app.route('/api/blockchain/status', methods=['GET'])
def get_blockchain_status():
    return jsonify({
        "chain_length": len(blockchain.chain),
        "pending_transactions": len(blockchain.pending_transactions),
        "is_valid": blockchain.is_chain_valid(),
        "difficulty": blockchain.difficulty
    })

@app.route('/api/blockchain/records', methods=['GET'])
def get_blockchain_records():
    farmer_id = request.args.get('farmer_id')
    records = blockchain.get_irrigation_records(farmer_id)
    return jsonify({"records": records, "count": len(records)})

@app.route('/api/sensor/all', methods=['GET'])
def get_all_sensors():
    return jsonify(sensor_aggregator.get_all_sensor_data())

@app.route('/api/irrigation/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    soil_moisture = data.get('soil_moisture')
    farmer_id = data.get('farmer_id', 'F001')
    if soil_moisture is None:
        return jsonify({"success": False, "message": "soil_moisture required"}), 400
    result = evaluate_irrigation(float(soil_moisture), farmer_id)
    return jsonify({"success": True, "result": result})

@app.route('/api/controller/start', methods=['POST'])
def start_controller():
    result = sensor_aggregator.controllers["CTRL_001"].start_irrigation()
    return jsonify({"success": True, "result": result})

@app.route('/api/controller/stop', methods=['POST'])
def stop_controller():
    result = sensor_aggregator.controllers["CTRL_001"].stop_irrigation()
    return jsonify({"success": True, "result": result})

@app.route('/api/controller/status', methods=['GET'])
def get_controller_status():
    status = sensor_aggregator.controllers["CTRL_001"].get_status()
    return jsonify({"success": True, "status": status})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    records = blockchain.get_irrigation_records()
    if not records:
        return jsonify({"total": 0, "avg_water": 0, "avg_moisture": 0, "chain_size": len(blockchain.chain)})
    water = [r.get("water_usage", 0) for r in records]
    moisture = [r.get("soil_moisture", 0) for r in records]
    return jsonify({
        "total_irrigation_events": len(records),
        "average_water_usage": round(sum(water) / len(water), 2),
        "average_soil_moisture": round(sum(moisture) / len(moisture), 2),
        "chain_size": len(blockchain.chain),
        "records": records[-5:]
    })
# ============================================================
# SOIL DETECTION ROUTES
# ============================================================

@app.route('/soil-detection')
@login_required
def soil_detection_page():
    return render_template('soil_detection.html')

@app.route('/api/soil/detect', methods=['POST'])
def detect_soil():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image uploaded"}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file type. Use JPG, PNG, or WEBP"}), 400

    try:
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        filename = f"soil_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        result = analyze_soil_image(filepath)

        if result["success"]:
            transaction = {
                "type": "soil_detection",
                "farmer_id": session.get('farmer_id', 'F001'),
                "soil_moisture": 0,
                "water_usage": 0,
                "status": "COMPLETED"
            }
            blockchain.add_transaction(transaction)
            blockchain.mine_pending_transactions("soil_analyzer")

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/soil/types', methods=['GET'])
def get_soil_types():
    return jsonify(SOIL_DATABASE)
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Agriculture Irrigation System")
    print("📡 http://localhost:5000")
    print("🔐 demo / demo123")
    print("=" * 50)
    app.run(debug=True, host='127.0.0.1', port=5000)