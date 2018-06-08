import json
import cloudevents
import requests
from flask import Flask, request, render_template
app = Flask(__name__)

class EventDB(object):
    def __init__(self):
        self.db = dict()

    def _get_list(self, k):
        if k in self.db:
            return self.db[k]
        else:
            l = list()
            self.db[k] = l
            return l

    def _add_to_list(self, k, v):
        self._get_list(k).append(v)

    def log_event(self, namespace, event):
        key = (namespace, event.event_type)
        self._add_to_list(key, event)
        self._add_to_list(namespace, event)

    def get_events_for_type(self, namespace, event_type):
        key = (namespace, event_type)
        return self._get_list(key)

    def get_events(self, namespace):
        return self._get_list(namespace)

    def all_keys(self):
        return self.db.keys()

db = EventDB()

def _keys_to_links(links):
    for link in links:
        if isinstance(link, tuple):
            href = "{}/events/{}/index.html".format(*link)
            title = "{}::{}".format(*link)
            yield dict(href=href, title=title)
        else:
            href = "{}/events.html".format(link)
            yield dict(href=href, title=link)


@app.route("/send", methods=["POST"])
def post():
    origin = request.form.get("origin")
    destination = request.form.get("destination")
    data = request.form.get("data")

    data_json = None
    try:
        data_json = json.loads(data)
    except:
        return "ERROR: Invalid JSON"

    event = None
    try:
        events = cloudevents.parse(data_json)
    except Exception as ex:
        return "ERROR parsing event as CloudEvent: {}".format(repr(ex))

    whd = cloudevents.WebhookDestination(origin, destination)

    whd_res = None
    try:
        whd_res = whd.send(events)
    except Exception as ex:
        return "ERROR sending event: {}".format(repr(ex))

    return "SUCCESS: {}".format(repr(whd_res))


@app.route("/")
def index():
    links = _keys_to_links(db.all_keys())
    return render_template("home.html", links=links)


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
        'WebHook-Allowed-Origin': '*',
        'Allow': 'OPTIONS,POST',
    }
    return ("Allowed!", 200, resp_headers)


@app.context_processor
def add_fns():
    def event_to_json(evt):
        return json.dumps(evt.to_dict(), indent=4, sort_keys=True)
    return dict(event_to_json=event_to_json)

@app.route("/<namespace>/events.html", methods=["GET"])
def events_html(namespace):
    events = db.get_events(namespace)
    return render_template("view-events.html", title=namespace, up="/", events=events)

@app.route("/<namespace>/events/<event_type>/index.html", methods=["GET"])
def events_by_type_html(namespace, event_type):
    events = db.get_events_for_type(namespace, event_type)
    return render_template(
        "view-events.html",
        title="{}::{}".format(namespace, event_type),
        up="/{ns}/events.html".format(ns=namespace),
        events=events
    )

@app.route("/<namespace>/recv", provide_automatic_options=False, methods=["POST", "OPTIONS"])
def receive_webhook(namespace):
    print(request.method)
    if request.method == "OPTIONS":
        return handle_options()
    elif request.method == "POST":
        print(request.headers)
        if request.json is None:
            return ("Only JSON bodies are support", 400)
        ce = cloudevents.parse(request.json)
        db.log_event(namespace, ce)
        return ("Got webhook!", 202)
    else:
        return ("method not allowed", 405)

app.run()
