DEFAULT_PORT = 47630
HOST = "127.0.0.1"


def page_url(port: int) -> str:
    return f"http://{HOST}:{port}/"


def page_key_name(port: int) -> str:
    return f"page-key-{port}"
