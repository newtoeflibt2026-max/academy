"""
Yamen Academy - Local Development Server
Runs API + WebApp + ngrok tunnel for Telegram Mini App testing
"""
import os, sys, subprocess, time
import threading

BASE = r"C:\yamen_academy"

def run_api_server():
    """Start Flask API server"""
    os.chdir(BASE)
    from api_server import app
    app.run(host="0.0.0.0", port=5000, debug=False)

def run_ngrok():
    """Start ngrok tunnel"""
    time.sleep(3)  # Wait for Flask to start
    try:
        from pyngrok import ngrok
        # Kill existing tunnels
        ngrok.kill()
        # Create new tunnel
        tunnel = ngrok.connect(5000, "http")
        public_url = tunnel.public_url
        print(f"\n{'='*60}")
        print(f"🌐 PUBLIC URL: {public_url}")
        print(f"📱 Mini App URL: {public_url}/index.html")
        print(f"🔗 Health: {public_url}/api/health")
        print(f"{'='*60}\n")
        
        # Update config.js with ngrok URL
        config_path = os.path.join(BASE, "webapp", "config.js")
        with open(config_path, "r", encoding="utf-8") as f:
            config = f.read()
        config = config.replace(
            'API_BASE: "https://yamen-academy.onrender.com"',
            f'API_BASE: "{public_url}"'
        )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config)
        print(f"✅ config.js updated with ngrok URL")
        
        # Keep tunnel alive
        while True:
            time.sleep(60)
    except ImportError:
        print("⚠️ pyngrok not installed. Install: pip install pyngrok")
        print("Alternative: Use localhost directly if on same network")
    except Exception as e:
        print(f"ngrok error: {e}")
        print("Try: ngrok http 5000  (in another terminal)")

if __name__ == "__main__":
    # Start API server in background
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Start ngrok
    run_ngrok()
