import socket
from http import server
from pathlib import Path


class TitleServer(server.HTTPServer):
    def __init__(self, title_path: str | Path, port: int | None = None):
        self.host = "localhost"
        self.port = port or self.find_free_port()
        title_path = Path(title_path)
        self.title_path = title_path

        class TitlePathHandler(server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=title_path, **kwargs)

        super().__init__((self.host, self.port), TitlePathHandler)

    def find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]
