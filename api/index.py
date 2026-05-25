from http.server import BaseHTTPRequestHandler
import os
import json
from discord_interactions import verify_key

# Vercel'e ekleyeceğimiz Public Key'i buradan alacak
PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Discord'un güvenlik doğrulaması (Bunu yapmazsan Discord hep hata verir)
        signature = self.headers.get('X-Signature-Ed25519')
        timestamp = self.headers.get('X-Signature-Timestamp')
        
        if not signature or not timestamp:
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Anahtar eşleşiyor mu kontrol et
        if not verify_key(body, signature, timestamp, PUBLIC_KEY):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Invalid request signature')
            return

        data = json.loads(body.decode('utf-8'))

        # PING (Type 1) Handshake - Discord'un aradığı o lanet cevap
        if data.get('type') == 1:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'type': 1}).encode('utf-8'))
            return

        # Diğer her şey için 200 OK dön
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
