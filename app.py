import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

@app.route('/')
@app.route('/index.html')
def index():
    return send_from_directory('webapp', 'index.html')

@app.route('/webapp/<path:path>')
def webapp_files(path):
    return send_from_directory('webapp', path)

@app.route('/admin_panel/')
@app.route('/admin_panel/index.html')
def admin_panel():
    return send_from_directory('admin_panel', 'index.html')

@app.route('/admin_panel/<path:path>')
def admin_panel_files(path):
    return send_from_directory('admin_panel', path)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "Yamen Academy API"})

# Import and register api_server routes
try:
    from api_server import register_routes
    register_routes(app)
except Exception as e:
    print(f"Warning: api_server routes not loaded: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'Starting on port {port}...')
    app.run(host='0.0.0.0', port=port)
