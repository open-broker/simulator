import requests
from flask import Flask, request
app = Flask(__name__)

@app.route("/")
def hello():
    return "open-broker simulator"

def handle_options():
    if 'WebHook-Request-Callback' in request.headers:
        url = request.headers["Webhook-Request-Callback"]
        try:
            ping = requests.get(url)
            if not ping.ok:
                print("Response not OK pinging Webhook-Request-Callback at URL '{}'".format(url))
        except:
            print("Something went wrong pining Webhook-Request-Callback at URL '{}'".format(url))

    resp_headers = {
        'WebHook-Request-Origin': '*',
        'Allow': 'OPTIONS,POST',
    }
    return ("Allowed!", 200, resp_headers)


@app.route("/<namespace>/recv", provide_automatic_options=False, methods=["POST", "OPTIONS"])
def receive_webhook(namespace):
    print(request.method)
    if request.method == "OPTIONS":
        return handle_options()
    elif request.method == "POST":
        if request.json is None:
            return ("Only JSON bodies are support", 400)
        return ("Got webhook!", 202)
    else:
        return ("method not allowed", 405)

app.run()
