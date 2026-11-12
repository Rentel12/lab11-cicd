import os
import socket

from flask import Flask

app = Flask(__name__)
VERSION = os.environ.get("APP_VERSION", "dev")


def greet(name: str) -> str:
    """Small pure function so we have something to unit-test."""
    return f"Hello, {name.strip().title()}!"


@app.get("/")
def index():
    return {"host": socket.gethostname(), "greeting": greet("narxoz")}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": VERSION}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
