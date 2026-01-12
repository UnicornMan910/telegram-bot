from flask import Flask

app = Flask(__name__)

@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "OK", 200
