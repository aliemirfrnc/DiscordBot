from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

class İbneRenderİcinSahteSite(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot tas gibi ayakta amina koyayim!")

def run_server():
    # Render'ın kendi verdiği portu kullanıyoruz, yoksa 8080
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), İbneRenderİcinSahteSite)
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
