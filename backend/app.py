from flask import Flask, jsonify, Response
from flask_cors import CORS
import json
import subprocess
import os
import logging
import threading
import time

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)

process = None
output_buffer = []
stop_event = threading.Event()
last_read_index = 0

def run_avalanche_script():
    global process, output_buffer
    avalanche_dir = os.path.join(os.path.dirname(__file__), 'Avalanche')
    command = "python main.py --config ./config/config.yaml --log-level INFO --interval 1"
    
    process = subprocess.Popen(
        command,
        shell=True,
        cwd=avalanche_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    for line in iter(process.stdout.readline, ''):
        output_buffer.append(line)
        if stop_event.is_set():
            break
    
    process.stdout.close()
    process.wait()

@app.route('/start-flask', methods=['POST'])
def start_flask():
    global process, output_buffer, stop_event
    logging.debug("Received POST request to /start-flask")
    try:
        if process is None or process.poll() is not None:
            output_buffer = []
            stop_event.clear()
            thread = threading.Thread(target=run_avalanche_script)
            thread.start()
            time.sleep(2)  # Give the script a moment to start
            return jsonify({'status': 'running', 'output': ''.join(output_buffer)}), 200
        else:
            return jsonify({'status': 'already_running', 'output': ''.join(output_buffer)}), 200
    
    except Exception as e:
        logging.error(f"Error in /start-flask: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500

def get_new_output():
    global output_buffer, last_read_index
    if last_read_index < len(output_buffer):
        new_output = ''.join(output_buffer[last_read_index:])
        last_read_index = len(output_buffer)
        return new_output
    return ''

@app.route('/stream-output')
def stream_output():
    def generate():
        while True:
            new_output = get_new_output()
            if new_output:
                yield f"data: {json.dumps({'output': new_output})}\n\n"
            time.sleep(0.1)  # Adjust as needed

    return Response(generate(), mimetype='text/event-stream')

@app.route('/stop-flask', methods=['POST'])
def stop_flask():
    global process, stop_event
    if process is not None:
        stop_event.set()
        process.terminate()
        process.wait()
        process = None
    return jsonify({'status': 'stopped'}), 200

def shutdown_server():
    global process, stop_event
    if process is not None:
        stop_event.set()
        process.terminate()
        process.wait()

if __name__ == '__main__':
    try:
        app.run(debug=True, host='localhost', port=5000)
    finally:
        shutdown_server()
