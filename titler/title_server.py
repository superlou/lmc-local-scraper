import socket
import urllib.parse
from http import server
from pathlib import Path

from jinja2 import Template


class TitleServer(server.HTTPServer):
    def __init__(self, title_path: str | Path, port: int | None = None):
        self.host = "localhost"
        self.port = port or self.find_free_port()
        title_path = Path(title_path)
        self.title_path = title_path
        self.root = title_path.parent

        super().__init__((self.host, self.port), TitleServerRequestHandler)

    def find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]


class TitleServerRequestHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        root = self.server.root
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qsl(parsed_url.query)
        file_path = root / parsed_url.path[1:]  # Remove leading "/"
        print(query)

        if file_path.exists():
            file_contents = open(file_path, "rb").read()
        elif template_path := file_path.with_suffix(file_path.suffix + ".jinja2"):
            template_contents = open(template_path).read()
            template = Template(template_contents)
            print(template)
            file_contents = template.render(text="something").encode()
        else:
            self.send_error(404, f"Path not found: {self.path}")
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(file_contents)
