
import os
import sys
import subprocess
import threading

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from PIL import Image
import requests
import io
import re

# USE_OVERLAY = True
USE_OVERLAY = False

# Esri tile sources
IMAGERY_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
LABELS_URL  = "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Reference_Overlay/MapServer/tile/{z}/{y}/{x}"

IMAGERY_EXPIRE_SECONDS = 7 * 24 * 60 * 60 # 1 week

at_d_cache = None
server_inst = None

class TileHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global at_d_cache

        parsed = urlparse(self.path)
        match = re.match(r'^/tile/(\d+)/(\d+)/(\d+)\.png$', parsed.path)
        if not match:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Invalid tile path. Use /tile/{z}/{y}/{x}.png')
            return

        z, y, x = map(int, match.groups())

        try:
            # Fetch imagery tile
            img_url = IMAGERY_URL.format(z=z, y=y, x=x)
            if USE_OVERLAY:
              lbl_url = LABELS_URL.format(z=z, y=y, x=x)

            img_bytes = at_d_cache.get(img_url, None)
            if img_bytes is None:
              img_bytes = requests.get(img_url).content
              at_d_cache.set(img_url, img_bytes, expire=IMAGERY_EXPIRE_SECONDS)

            if USE_OVERLAY:
              lbl_bytes = at_d_cache.get(lbl_url, None)
              if lbl_bytes is None:
                lbl_bytes = requests.get(lbl_url).content
                at_d_cache.set(lbl_url, lbl_bytes, expire=IMAGERY_EXPIRE_SECONDS)

            base_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            if USE_OVERLAY:
              overlay_img = Image.open(io.BytesIO(lbl_bytes)).convert("RGBA")

            # Composite tiles
            if USE_OVERLAY:
              composed = Image.alpha_composite(base_img, overlay_img)
            else:
              composed = base_img

            # Respond with PNG
            img_bytes = io.BytesIO()
            composed.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.send_header("Content-length", str(len(img_bytes.getvalue())))
            self.end_headers()
            self.wfile.write(img_bytes.read())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error fetching/composing tile: {e}".encode("utf-8"))

     # Suppress all logging output
    def log_message(self, format, *args):
        pass


def shutdown():
  global server_inst
  if server_inst is not None:
    server_inst.shutdown()

def run(d_cache, port):
  global at_d_cache, server_inst
  at_d_cache = d_cache
  httpd = HTTPServer(('127.0.0.1', port), TileHandler)
  print(f"Serving tile proxy at http://localhost:{port}/tile/z/y/x.png")
  server_inst = httpd
  httpd.serve_forever()

def spawn_run_thread(d_cache, port):
  t = threading.Thread(target=run, args=(d_cache, port))
  t.start()
  return t

