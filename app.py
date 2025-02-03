from flask import Flask, request, jsonify
from utils.turtle_parser import Parser
import os
import threading
import time
import socket
import dotenv
import os

dotenv.load_dotenv()

app = Flask(__name__)
currentlyRunningProgram = False

@app.route("/")
def home():
    return "Hello, World!"

def process_program(source):
    global currentlyRunningProgram

    parser = Parser(source=source)
    history = parser.getParsedResult()

    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    s.connect((os.getenv("MAC_ADDRSS"), 1))

    for item in history:
        commandstr = item[0] + f" {str(item[1])}" if len(item) > 1 else ""
        s.send(commandstr.encode())
        if item[0] == "fd" or item[0] == "bk":
            ## considering 100 setps takes 10 seconds, we can calculate the time taken for each step
            time.sleep(item[1]/10)
        if item[0] == "rt" or item[0] == "lt":
            steps = item[1]
            time.sleep(steps*10/90)

    currentlyRunningProgram = False


@app.route('/start', methods=['POST'])
def start_execution():
    global currentlyRunningProgram
    if currentlyRunningProgram:
        return jsonify({"status": "failed", "message": "Another program is already running"}), 400
    currentlyRunningProgram = True

    """Start execution in a separate thread"""
    program_data = request.form.get('program', [])
    
    # Start a background thread
    thread = threading.Thread(target=process_program, args=(program_data,))
    thread.start()
    
    return jsonify({"status": "running", "message": "Execution started"}), 202

## create a simple html page to input the program
@app.route('/input', methods=['GET'])
def input_program():
    return """
    <html>
    <body>
    <h1>Enter your program</h1>
    <form action="/start" method="post">
        <textarea name="program" rows="10" cols="50"></textarea>
        <input type="submit" value="Submit">
    </form>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(debug=True)
