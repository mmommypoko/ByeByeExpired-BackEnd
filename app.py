from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import Flask, send_from_directory
import os
from werkzeug.utils import secure_filename
import traceback
from datetime import datetime, timedelta
from bson import ObjectId

# MongoDB Connection URI
uri = "mongodb+srv://ByeByeExpired:VlbKjtFuYvgw0lAS@cluster0.rcivs.mongodb.net/?retryWrites=true&w=majority&ssl=true&tlsAllowInvalidCertificates=true"

# Connect to MongoDB
client = MongoClient(uri)
db = client["ByeByeExpired"]
users_collection = db['users']
items_collection = db['items']

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello_world():
    return "Hello! Welcome to Back-End \"ByeByeExpired\""

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# 📌 API อัปโหลดรูป
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        file_url = f"https://cuddly-space-lamp-jj4jqr7jvg5q2qvpg-5000.app.github.dev/uploads/{filename}"

        return jsonify({"message": "File uploaded successfully", "file_url": file_url}), 201

    return jsonify({"message": "Invalid file type"}), 400

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ฟังก์ชันสำหรับสร้าง user_id โดยใช้จำนวนผู้ใช้ในระบบ
def get_next_user_id():
    user_count = users_collection.count_documents({})
    return user_count + 1  # user_id จะเริ่มต้นจาก 1 และเพิ่มขึ้นทุกครั้ง

# API สำหรับการลงทะเบียน
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # ตรวจสอบอีเมลว่าอยู่ในระบบแล้วหรือยัง
    existing_user = users_collection.find_one({"email": data['email']})
    if existing_user:
        return jsonify({"message": "Email already exists"}), 400

    if data['password'] != data['confirmPassword']:
        return jsonify({"message": "Passwords do not match"}), 400

    # ใช้ฟังก์ชัน get_next_user_id ในการเพิ่ม user_id
    new_user_id = get_next_user_id()

    user = {
        "user_id": new_user_id,  # กำหนด user_id จากการคำนวณ
        "full_name": data['fullName'],
        "email": data['email'],
        "password": generate_password_hash(data['password']),
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user)
    
    return jsonify({"message": "User registered successfully", "user_id": new_user_id}), 201

# API สำหรับการล็อคอิน
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # รับข้อมูลจาก request body (JSON)

    # ค้นหาผู้ใช้ในฐานข้อมูลด้วยอีเมล
    user = users_collection.find_one({"email": data['email']})
    
    # ตรวจสอบผู้ใช้และรหัสผ่าน
    if user and check_password_hash(user['password'], data['password']):
        # ส่งข้อมูล user_id และข้อมูลอื่น ๆ กลับไป
        return jsonify({
            "message": "Login successful",
            "user": {
                "user_id": user['user_id'],  # ใช้ user_id แทน _id
                "full_name": user['full_name'],
                "email": user['email']
            }
        }), 200
    
    # หากไม่พบผู้ใช้หรือรหัสผ่านไม่ถูกต้อง
    return jsonify({"message": "Invalid email or password"}), 400

# API สำหรับดึงข้อมูลสินค้าของผู้ใช้
@app.route('/get_items/<user_id>', methods=['GET'])
def get_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer
        # ดึงข้อมูลสินค้าของผู้ใช้และเรียงลำดับตาม expiration_date
        items = list(items_collection.find({"user_id": user_id}).sort("expiration_date", 1))
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
        return jsonify(items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

# API สำหรับการเพิ่มสินค้า
@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        data = request.get_json()
        print("Received data:", data)  # เพิ่ม log เพื่อตรวจสอบข้อมูลที่รับมา

        required_fields = ['name', 'storage', 'storage_date', 'expiration_date', 'quantity', 'note']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400

        # ตรวจสอบว่า user_id เป็นตัวเลขหรือไม่
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"message": "Invalid user_id. Must be an integer."}), 400

        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({"message": "User not found"}), 400

        try:
            storage_date = datetime.strptime(data['storage_date'], "%Y-%m-%d")
            expiration_date = datetime.strptime(data['expiration_date'], "%Y-%m-%d")
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD."}), 400
        
        item = {
            "photo": data.get('photo'),
            "name": data.get('name'),
            "storage": data.get('storage'),
            "storage_date": storage_date,
            "expiration_date": expiration_date,
            "quantity": int(data.get('quantity')),
            "note": data.get('note'),
            "user_id": user_id
        }

        result = items_collection.insert_one(item)
        return jsonify({"message": "Item added successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับดึงข้อมูลผู้ใช้ทั้งหมด
@app.route('/get_user/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer
        user = users_collection.find_one({"user_id": user_id})
        if user:
            return jsonify({
                "name": user.get("full_name"),
                "email": user.get("email")
            }), 200
        else:
            return jsonify({"message": "User not found"}), 404
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
@app.route('/update_name', methods=['PUT'])
def update_name():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_name = data.get('name')

        if not user_id or not new_name:
            return jsonify({"message": "Missing user_id or name"}), 400

        user_id = int(user_id)  # แปลง user_id เป็น integer
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"full_name": new_name}}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Name updated successfully"}), 200
        else:
            return jsonify({"message": "User not found or no changes made"}), 404
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับการลบบัญชีผู้ใช้
@app.route('/delete_account', methods=['DELETE'])
def delete_account():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"message": "Missing user_id"}), 400

        user_id = int(user_id)  # แปลง user_id เป็น integer
        # ลบข้อมูลผู้ใช้
        result = users_collection.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            # ลบข้อมูลสินค้าที่เชื่อมโยงกับผู้ใช้
            items_collection.delete_many({"user_id": user_id})
            return jsonify({"message": "Account deleted successfully"}), 200
        else:
            return jsonify({"message": "User not found"}), 404
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
@app.route('/get_expired_items/<user_id>', methods=['GET'])
def get_expired_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer
        current_date = datetime.utcnow()  # วันที่ปัจจุบัน

        # ดึงสินค้าที่หมดอายุแล้ว (expiration_date < current_date) และเรียงลำดับตาม expiration_date
        expired_items = list(items_collection.find({
            "user_id": user_id,
            "expiration_date": {"$lt": current_date}
        }).sort("expiration_date", 1))  # เรียงจากน้อยไปมาก

        for item in expired_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(expired_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route('/get_nearly_expired_items/<user_id>', methods=['GET'])
def get_nearly_expired_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer
        current_date = datetime.utcnow()  # วันที่ปัจจุบัน
        five_days_later = current_date + timedelta(days=5)  # วันที่ปัจจุบัน + 5 วัน

        # ดึงสินค้าที่กำลังหมดอายุภายใน 5 วัน (current_date <= expiration_date <= five_days_later) และเรียงลำดับตาม expiration_date
        nearly_expired_items = list(items_collection.find({
            "user_id": user_id,
            "expiration_date": {
                "$gte": current_date,
                "$lte": five_days_later
            }
        }).sort("expiration_date", 1))  # เรียงจากน้อยไปมาก

        for item in nearly_expired_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(nearly_expired_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route('/get_dry_food_items/<user_id>', methods=['GET'])
def get_dry_food_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer

        # ดึงสินค้าที่มี storage เป็น "DryFood" และเรียงลำดับตาม expiration_date
        dry_food_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "dry_food"  # เงื่อนไขสำหรับ storage เป็น DryFood
        }).sort("expiration_date", 1))  # เรียงจากน้อยไปมาก

        for item in dry_food_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(dry_food_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
@app.route('/get_freezer_items/<user_id>', methods=['GET'])
def get_freezer_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer

        # ดึงสินค้าที่มี storage เป็น "freezer" และเรียงลำดับตาม expiration_date
        freezer_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "freezer"  # เงื่อนไขสำหรับ storage เป็น freezer
        }).sort("expiration_date", 1))  # เรียงจากน้อยไปมาก

        for item in freezer_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(freezer_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
@app.route('/get_fridge_items/<user_id>', methods=['GET'])
def get_fridge_items(user_id):
    try:
        user_id = int(user_id)  # แปลง user_id เป็น integer

        # ดึงสินค้าที่มี storage เป็น "fridge" และเรียงลำดับตาม expiration_date
        fridge_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "fridge"  # เงื่อนไขสำหรับ storage เป็น fridge
        }).sort("expiration_date", 1))  # เรียงจากน้อยไปมาก

        for item in fridge_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(fridge_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
from bson import ObjectId
from datetime import datetime

@app.route('/update_item/<item_id>', methods=['PUT'])
def update_item(item_id):
    try:
        data = request.get_json()
        print("Received data:", data)  # Log ข้อมูลที่ได้รับ

        # ตรวจสอบว่ามีข้อมูลที่จำเป็นหรือไม่
        if not data:
            return jsonify({"message": "No data provided"}), 400

        # แปลง _id เป็น ObjectId
        try:
            item_id = ObjectId(item_id)
        except Exception as e:
            return jsonify({"message": "Invalid item_id format"}), 400

        # แปลง user_id เป็น integer (ถ้ามี)
        if 'user_id' in data:
            try:
                data['user_id'] = int(data['user_id'])
            except ValueError:
                return jsonify({"message": "Invalid user_id. Must be an integer."}), 400

        # แปลงวันที่จาก ISO string เป็น datetime object (ถ้ามี)
        if 'storage_date' in data:
            try:
                data['storage_date'] = datetime.strptime(data['storage_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                return jsonify({"message": "Invalid storage_date format. Use ISO string."}), 400

        if 'expiration_date' in data:
            try:
                data['expiration_date'] = datetime.strptime(data['expiration_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                return jsonify({"message": "Invalid expiration_date format. Use ISO string."}), 400

        # อัปเดตข้อมูลในฐานข้อมูล
        result = items_collection.update_one(
            {"_id": item_id},
            {"$set": data}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Item updated successfully"}), 200
        else:
            return jsonify({"message": "No changes made or item not found"}), 404

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"message": "Internal server error"}), 500
    
@app.route('/delete_item/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    try:
        items_collection.delete_one({"_id": ObjectId(item_id)})
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)