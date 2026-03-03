from flask import Flask
import threading
import time
from config import PORT

app = Flask(__name__)

@app.route('/')
def home():
    return "Serena Downloader Bot is running."

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def start_flask():
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()
