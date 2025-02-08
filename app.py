from flask import Flask, request, jsonify
from utils.turtle_parser import Parser
from utils.codetocommands import codetocommands
import os
import threading
import time
import socket
import dotenv
import os
from flask_cors import CORS

dotenv.load_dotenv()

platform = os.getenv("PLATFORM", "raspberrypi")

app = Flask(__name__, static_folder='static', static_url_path='/')
currentlyRunningProgram = False

CORS(app)



def process_program(source):
    global currentlyRunningProgram
    try:
        commands = codetocommands(source)

        s = None
        if platform == "windows":
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            s.connect((os.getenv("MAC_ADDRESS"), 1))

        print("Begin execution")

        for item in commands:
            commandstr = item[0] + f" {str(item[1])}" if len(item) > 1 else ""

            if platform == "windows" and s:
                s.send(commandstr.encode())
            elif platform == "raspberrypi":
                os.system(f"echo '{commandstr}' > /dev/rfcomm0")

            if item[0] == "fd" or item[0] == "bk":
                ## considering 100 setps takes 10 seconds, we can calculate the time taken for each step
                time.sleep(item[1]/10)
            elif item[0] == "rt" or item[0] == "lt":
                steps = item[1]
                time.sleep(steps*10/90)
            else:
                ## for other commands like pu, pd, we can sleep for 1 second
                time.sleep(1)
        
        if platform == "windows" and s:
            s.close()

        print("Program Execution Complete")

    except Exception as e:
        print(f"Exception occured during exceution: {e}")
        currentlyRunningProgram = False

    currentlyRunningProgram = False


@app.route('/start', methods=['POST'])
def start_execution():
    global currentlyRunningProgram
    if currentlyRunningProgram:
        return jsonify({"status": "failed", "message": "Another program is already running"}), 400
    currentlyRunningProgram = True

    """Start execution in a separate thread"""
    program_data = request.form.get('program', [])
    if request.is_json:
        program_data = request.json.get('program', [])

    print(f"Recieved Program: {program_data}")
    
    # Start a background thread
    thread = threading.Thread(target=process_program, args=(program_data,))
    thread.start()
    
    return jsonify({"status": "running", "message": "Execution started"}), 202

## create a simple html page to input the program
@app.route('/input', methods=['GET'])
def input_program():
    return app.send_static_file('input.html')

@app.route("/")
@app.route("/<path>")
def home(path=""):
    return app.send_static_file('index.html')


if __name__ == "__main__":
    app.run(debug=True)
