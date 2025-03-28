from flask import Flask, request, jsonify
from flask_cors import CORS  # อนุญาตให้มีการเรียก API ข้ามโดเมน
from pymongo import MongoClient  # สำหรับเชื่อมต่อกับ MongoDB
from werkzeug.security import generate_password_hash, check_password_hash  # สำหรับเข้ารหัสรหัสผ่าน
from datetime import datetime
from flask import Flask, send_from_directory  # สำหรับส่งไฟล์จากไดเรกทอรี
import os
from werkzeug.utils import secure_filename  # สำหรับทำให้ชื่อไฟล์ปลอดภัย
import traceback  # สำหรับแสดงข้อผิดพลาดแบบละเอียด
from datetime import datetime, timedelta  # สำหรับทำงานกับวันที่
from bson import ObjectId  # สำหรับทำงานกับ ObjectId ของ MongoDB

# MongoDB Connection URI - เชื่อมต่อกับ MongoDB Atlas
uri = "mongodb+srv://ByeByeExpired:VlbKjtFuYvgw0lAS@cluster0.rcivs.mongodb.net/?retryWrites=true&w=majority&ssl=true&tlsAllowInvalidCertificates=true"

# เชื่อมต่อกับ MongoDB
client = MongoClient(uri)
db = client["ByeByeExpired"]  # เลือกฐานข้อมูล
users_collection = db['users']  # คอลเลกชันผู้ใช้
items_collection = db['items']  # คอลเลกชันสินค้า

app = Flask(__name__)
CORS(app)  # เปิดใช้งาน CORS สำหรับแอปทั้งหมด

@app.route("/")
def hello_world():
    return "Hello! Welcome to Back-End \"ByeByeExpired\""

# ตั้งค่าสำหรับการอัปโหลดไฟล์
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # สร้างโฟลเดอร์ถ้ายังไม่มี

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}  # ชนิดไฟล์ที่อนุญาต

def allowed_file(filename):
    """ตรวจสอบว่าไฟล์มีส่วนขยายที่อนุญาตหรือไม่"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# 📌 API สำหรับอัปโหลดรูปภาพ
@app.route("/upload", methods=["POST"])
def upload_file():
    """จัดการการอัปโหลดไฟล์ภาพ"""
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # ทำให้ชื่อไฟล์ปลอดภัย
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        # สร้าง URL สำหรับเข้าถึงไฟล์
        file_url = f"https://fuzzy-space-giggle-pjw99rqj6ww5hgrg-5000.app.github.dev/uploads/{filename}"

        return jsonify({"message": "File uploaded successfully", "file_url": file_url}), 201

    return jsonify({"message": "Invalid file type"}), 400

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """ส่งไฟล์ที่อัปโหลดแล้วให้กับผู้ใช้"""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ฟังก์ชันสำหรับสร้าง user_id ใหม่
def get_next_user_id():
    """สร้าง user_id ใหม่โดยนับจำนวนผู้ใช้ที่มีอยู่แล้ว"""
    user_count = users_collection.count_documents({})
    return user_count + 1  # user_id จะเริ่มจาก 1 และเพิ่มขึ้นเรื่อยๆ

# API สำหรับการลงทะเบียนผู้ใช้ใหม่
@app.route('/register', methods=['POST'])
def register():
    """ลงทะเบียนผู้ใช้ใหม่"""
    data = request.get_json()

    # ตรวจสอบว่าอีเมลนี้มีอยู่แล้วหรือไม่
    existing_user = users_collection.find_one({"email": data['email']})
    if existing_user:
        return jsonify({"message": "Email already exists"}), 400

    if data['password'] != data['confirmPassword']:
        return jsonify({"message": "Passwords do not match"}), 400

    # สร้าง user_id ใหม่
    new_user_id = get_next_user_id()

    user = {
        "user_id": new_user_id,
        "full_name": data['fullName'],
        "email": data['email'],
        "password": generate_password_hash(data['password']),  # เข้ารหัสรหัสผ่าน
        "created_at": datetime.utcnow()  # เก็บเวลาที่สร้าง
    }
    result = users_collection.insert_one(user)
    
    return jsonify({"message": "User registered successfully", "user_id": new_user_id}), 201

# API สำหรับการเข้าสู่ระบบ
@app.route('/login', methods=['POST'])
def login():
    """จัดการการเข้าสู่ระบบ"""
    data = request.get_json()

    # ค้นหาผู้ใช้ด้วยอีเมล
    user = users_collection.find_one({"email": data['email']})
    
    # ตรวจสอบรหัสผ่าน
    if user and check_password_hash(user['password'], data['password']):
        # ส่งข้อมูลผู้ใช้กลับไป (ไม่รวมรหัสผ่าน)
        return jsonify({
            "message": "Login successful",
            "user": {
                "user_id": user['user_id'],
                "full_name": user['full_name'],
                "email": user['email']
            }
        }), 200
    
    return jsonify({"message": "Invalid email or password"}), 400

# API สำหรับดึงข้อมูลสินค้าของผู้ใช้
@app.route('/get_items/<user_id>', methods=['GET'])
def get_items(user_id):
    """ดึงรายการสินค้าของผู้ใช้ เรียงตามวันหมดอายุ"""
    try:
        user_id = int(user_id)  # แปลง user_id เป็นตัวเลข
        # ค้นหาสินค้าของผู้ใช้และเรียงตามวันหมดอายุ (จากเร็วไปช้า)
        items = list(items_collection.find({"user_id": user_id}).sort("expiration_date", 1))
        # แปลง ObjectId และ user_id เป็น string ก่อนส่งกลับ
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
        return jsonify(items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

# API สำหรับเพิ่มสินค้าใหม่
@app.route('/add_item', methods=['POST'])
def add_item():
    """เพิ่มสินค้าใหม่ลงในฐานข้อมูล"""
    try:
        data = request.get_json()
        print("Received data:", data)  # Log ข้อมูลที่ได้รับ

        # ตรวจสอบว่ามีข้อมูลที่จำเป็นครบหรือไม่
        required_fields = ['name', 'storage', 'storage_date', 'expiration_date', 'quantity', 'note']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"message": "User ID is required"}), 400

        try:
            user_id = int(user_id)  # แปลง user_id เป็นตัวเลข
        except ValueError:
            return jsonify({"message": "Invalid user_id. Must be an integer."}), 400

        # ตรวจสอบว่าผู้ใช้มีอยู่จริงหรือไม่
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({"message": "User not found"}), 400

        try:
            # แปลงวันที่จาก string เป็น datetime object
            storage_date = datetime.strptime(data['storage_date'], "%Y-%m-%d")
            expiration_date = datetime.strptime(data['expiration_date'], "%Y-%m-%d")
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD."}), 400
        
        # สร้างออบเจ็กต์สินค้าใหม่
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

        # เพิ่มสินค้าใหม่ลงในฐานข้อมูล
        result = items_collection.insert_one(item)
        return jsonify({"message": "Item added successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()  # พิมพ์ข้อผิดพลาดแบบละเอียด
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับดึงข้อมูลผู้ใช้
@app.route('/get_user/<user_id>', methods=['GET'])
def get_user(user_id):
    """ดึงข้อมูลผู้ใช้จาก user_id"""
    try:
        user_id = int(user_id)
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
    
# API สำหรับอัปเดตชื่อผู้ใช้
@app.route('/update_name', methods=['PUT'])
def update_name():
    """อัปเดตชื่อผู้ใช้"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_name = data.get('name')

        if not user_id or not new_name:
            return jsonify({"message": "Missing user_id or name"}), 400

        user_id = int(user_id)
        # อัปเดตชื่อผู้ใช้ในฐานข้อมูล
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
    
# API สำหรับลบบัญชีผู้ใช้
@app.route('/delete_account', methods=['DELETE'])
def delete_account():
    """ลบบัญชีผู้ใช้และสินค้าที่เกี่ยวข้อง"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"message": "Missing user_id"}), 400

        user_id = int(user_id)
        # ลบผู้ใช้จากฐานข้อมูล
        result = users_collection.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            # ลบสินค้าทั้งหมดของผู้ใช้นี้
            items_collection.delete_many({"user_id": user_id})
            return jsonify({"message": "Account deleted successfully"}), 200
        else:
            return jsonify({"message": "User not found"}), 404
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับดึงสินค้าที่หมดอายุแล้ว
@app.route('/get_expired_items/<user_id>', methods=['GET'])
def get_expired_items(user_id):
    """ดึงสินค้าที่หมดอายุแล้ว เรียงตามวันหมดอายุ"""
    try:
        user_id = int(user_id)
        current_date = datetime.utcnow()  # วันที่ปัจจุบัน

        # ค้นหาสินค้าที่หมดอายุแล้ว (วันที่หมดอายุน้อยกว่าวันปัจจุบัน)
        expired_items = list(items_collection.find({
            "user_id": user_id,
            "expiration_date": {"$lt": current_date}
        }).sort("expiration_date", 1))  # เรียงจากเร็วไปช้า

        # แปลงข้อมูลเพื่อให้ส่งเป็น JSON ได้
        for item in expired_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(expired_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

# API สำหรับดึงสินค้าที่ใกล้หมดอายุ (ภายใน 5 วัน)
@app.route('/get_nearly_expired_items/<user_id>', methods=['GET'])
def get_nearly_expired_items(user_id):
    """ดึงสินค้าที่จะหมดอายุภายใน 5 วัน"""
    try:
        user_id = int(user_id)
        current_date = datetime.utcnow()
        five_days_later = current_date + timedelta(days=5)  # วันที่ปัจจุบัน + 5 วัน

        # ค้นหาสินค้าที่จะหมดอายุภายใน 5 วัน
        nearly_expired_items = list(items_collection.find({
            "user_id": user_id,
            "expiration_date": {
                "$gte": current_date,  # มากกว่าหรือเท่ากับวันนี้
                "$lte": five_days_later  # น้อยกว่าหรือเท่ากับ 5 วันข้างหน้า
            }
        }).sort("expiration_date", 1))  # เรียงจากเร็วไปช้า

        for item in nearly_expired_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(nearly_expired_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

# API สำหรับดึงสินค้าประเภทอาหารแห้ง
@app.route('/get_dry_food_items/<user_id>', methods=['GET'])
def get_dry_food_items(user_id):
    """ดึงสินค้าประเภทอาหารแห้ง"""
    try:
        user_id = int(user_id)

        # ค้นหาสินค้าที่เก็บในส่วนอาหารแห้ง
        dry_food_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "dry_food"
        }).sort("expiration_date", 1))

        for item in dry_food_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(dry_food_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับดึงสินค้าประเภทแช่แข็ง
@app.route('/get_freezer_items/<user_id>', methods=['GET'])
def get_freezer_items(user_id):
    """ดึงสินค้าประเภทแช่แข็ง"""
    try:
        user_id = int(user_id)

        # ค้นหาสินค้าที่เก็บในช่องแช่แข็ง
        freezer_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "freezer"
        }).sort("expiration_date", 1))

        for item in freezer_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(freezer_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับดึงสินค้าประเภทตู้เย็น
@app.route('/get_fridge_items/<user_id>', methods=['GET'])
def get_fridge_items(user_id):
    """ดึงสินค้าประเภทตู้เย็น"""
    try:
        user_id = int(user_id)

        # ค้นหาสินค้าที่เก็บในตู้เย็น
        fridge_items = list(items_collection.find({
            "user_id": user_id,
            "storage": "fridge"
        }).sort("expiration_date", 1))

        for item in fridge_items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])

        return jsonify(fridge_items), 200
    except ValueError:
        return jsonify({"message": "Invalid user_id. Must be an integer."}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    
# API สำหรับอัปเดตข้อมูลสินค้า
@app.route('/update_item/<item_id>', methods=['PUT'])
def update_item(item_id):
    """อัปเดตข้อมูลสินค้า"""
    try:
        data = request.get_json()
        print("Received data:", data)

        if not data:
            return jsonify({"message": "No data provided"}), 400

        try:
            item_id = ObjectId(item_id)  # แปลง string เป็น ObjectId
        except Exception as e:
            return jsonify({"message": "Invalid item_id format"}), 400

        # แปลง user_id เป็น integer ถ้ามี
        if 'user_id' in data:
            try:
                data['user_id'] = int(data['user_id'])
            except ValueError:
                return jsonify({"message": "Invalid user_id. Must be an integer."}), 400

        # แปลงวันที่จาก ISO string เป็น datetime object
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
    
# API สำหรับลบสินค้า
@app.route('/delete_item/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    """ลบสินค้าจากฐานข้อมูล"""
    try:
        items_collection.delete_one({"_id": ObjectId(item_id)})
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Internal server error"}), 500
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)  # เริ่มเซิร์ฟเวอร์ Flask