from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import firebase_admin
from firebase_admin import credentials, auth
import os

app = Flask(__name__)
CORS(app) # Allow frontend to communicate with backend
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///upsc_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# IMPORTANT: Place your Firebase Admin SDK private key JSON file in the same folder
# and name it 'serviceAccountKey.json'
if os.path.exists('serviceAccountKey.json'):
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
else:
    print("WARNING: serviceAccountKey.json not found! Auth routes will fail.")

class UserProgress(db.Model):
    id = db.Column(db.String(128), primary_key=True) # Firebase UID
    topics = db.Column(db.Text, default='{}')
    streak = db.Column(db.Text, default='{"count":0,"days":[]}')
    last_checkin = db.Column(db.String(64), default='')

with app.app_context():
    db.create_all()

def verify_token(req):
    token = req.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return None
    try:
        token = token.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except Exception as e:
        print("Token verification error:", e)
        return None

@app.route('/api/sync', methods=['POST'])
def sync_data():
    uid = verify_token(request)
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user = UserProgress.query.get(uid)
    if not user:
        user = UserProgress(id=uid)
        db.session.add(user)
    
    user.topics = data.get('topics', user.topics)
    user.streak = data.get('streak', user.streak)
    user.last_checkin = data.get('last_checkin', user.last_checkin)
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/load', methods=['GET'])
def load_data():
    uid = verify_token(request)
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = UserProgress.query.get(uid)
    if not user:
        return jsonify({'topics': '{}', 'streak': '{"count":0,"days":[]}', 'last_checkin': ''})
    
    return jsonify({
        'topics': user.topics,
        'streak': user.streak,
        'last_checkin': user.last_checkin
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)