from flask import Flask, render_template, jsonify
import speech_recognition as sr
import threading
import boto3
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)

recognizer = sr.Recognizer()
mic = sr.Microphone()
stop_event = threading.Event()
accumulated_text = ""

# AWS Translate client
translate = boto3.client('translate', region_name='us-east-1')  # Update region if needed

def listen():
    global accumulated_text
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while not stop_event.is_set():
            try:
                audio = recognizer.listen(source, timeout=1)
                recognized_text = recognizer.recognize_google(audio)
                accumulated_text += " " + recognized_text
            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                pass
            except sr.RequestError:
                pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start')
def start_listening():
    global stop_event
    if not hasattr(start_listening, "listening_thread") or not start_listening.listening_thread.is_alive():
        stop_event.clear()
        start_listening.listening_thread = threading.Thread(target=listen, daemon=True)
        start_listening.listening_thread.start()
    return jsonify({"status": "Started"})

@app.route('/stop')
def stop_listening():
    global stop_event
    stop_event.set()
    return jsonify({"status": "Stopped"})

@app.route('/text')
def get_text():
    return jsonify({"text": accumulated_text})

@app.route('/translate/<lang>')
def translate_text(lang):
    global accumulated_text
    try:
        result = translate.translate_text(
            Text=accumulated_text,
            SourceLanguageCode="en",
            TargetLanguageCode=lang
        )
        return jsonify({"text": result['TranslatedText']})
    except NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear')
def clear_text():
    global accumulated_text
    accumulated_text = ""
    return jsonify({"status": "Cleared"})

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
