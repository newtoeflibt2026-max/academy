from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/')
def home():
    return jsonify({'status':'ok','message':'Yamen Academy API'})
@app.route('/api/health')
def health():
    return jsonify({'status':'ok','service':'Yamen Academy API'})
