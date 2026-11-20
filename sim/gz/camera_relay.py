#!/usr/bin/env python3
"""Minimal Gazebo Harmonic camera -> HTTP JPEG/MJPEG relay running inside the PX4 container.

Subscribes to a Gazebo camera topic via gz.transport13 (preinstalled in the PX4 Docker image)
and serves frames over HTTP with exact simulation timestamps in headers:
  - GET /latest.jpg    -> single latest JPEG with X-Sim-Timestamp-Us, X-Frame-Seq, X-Width, X-Height
  - GET /stream.mjpeg  -> multipart/x-mixed-replace MJPEG stream with per-part headers
  - GET /health        -> JSON status
"""

from __future__ import annotations

import argparse
import io
import json
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

import numpy as np
from PIL import Image


class FrameBuffer:
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._jpeg: Optional[bytes] = None
        self._sim_us: int = 0
        self._seq: int = 0
        self._width: int = 0
        self._height: int = 0

    def update(self, jpeg: bytes, sim_us: int, width: int, height: int) -> None:
        with self._cond:
            self._jpeg = jpeg
            self._sim_us = sim_us
            self._seq += 1
            self._width = width
            self._height = height
            self._cond.notify_all()

    def latest(self) -> tuple[Optional[bytes], int, int, int, int]:
        with self._cond:
            return self._jpeg, self._sim_us, self._seq, self._width, self._height

    def wait_next(self, last_seq: int, timeout: float = 2.0) -> tuple[Optional[bytes], int, int, int, int]:
        with self._cond:
            self._cond.wait_for(lambda: self._seq > last_seq, timeout=timeout)
            return self._jpeg, self._sim_us, self._seq, self._width, self._height


def make_handler(buf: FrameBuffer):
    class CameraRelayHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/health":
                jpeg, sim_us, seq, width, height = buf.latest()
                payload = json.dumps(
                    {
                        "ready": jpeg is not None,
                        "seq": seq,
                        "sim_timestamp_us": sim_us,
                        "width": width,
                        "height": height,
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            if path == "/latest.jpg":
                jpeg, sim_us, seq, width, height = buf.latest()
                if jpeg is None:
                    self.send_response(503)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg)))
                self.send_header("X-Sim-Timestamp-Us", str(sim_us))
                self.send_header("X-Frame-Seq", str(seq))
                self.send_header("X-Width", str(width))
                self.send_header("X-Height", str(height))
                self.end_headers()
                self.wfile.write(jpeg)
                return

            if path == "/stream.mjpeg":
                boundary = b"suasframe"
                self.send_response(200)
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary.decode()}")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                last_seq = 0
                try:
                    while True:
                        jpeg, sim_us, seq, width, height = buf.wait_next(last_seq, timeout=2.0)
                        if jpeg is None or seq == last_seq:
                            continue
                        last_seq = seq
                        part_header = (
                            b"--" + boundary + b"\r\n"
                            + b"Content-Type: image/jpeg\r\n"
                            + f"Content-Length: {len(jpeg)}\r\n".encode("ascii")
                            + f"X-Sim-Timestamp-Us: {sim_us}\r\n".encode("ascii")
                            + f"X-Frame-Seq: {seq}\r\n".encode("ascii")
                            + f"X-Width: {width}\r\n".encode("ascii")
                            + f"X-Height: {height}\r\n\r\n".encode("ascii")
                        )
                        self.wfile.write(part_header)
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return

            self.send_response(404)
            self.end_headers()

    return CameraRelayHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge Gazebo Harmonic camera topic to HTTP JPEG/MJPEG.")
    parser.add_argument("--topic", default="/camera", help="Gazebo image topic (default: /camera)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8554, help="HTTP port (default: 8554)")
    parser.add_argument("--quality", type=int, default=92, help="JPEG quality 1-95")
    args = parser.parse_args()

    from gz.msgs10.image_pb2 import Image as GzImage
    from gz.transport13 import Node

    buf = FrameBuffer()
    node = Node()

    def on_image(msg: GzImage) -> None:
        w, h = int(msg.width), int(msg.height)
        if w <= 0 or h <= 0 or not msg.data:
            return
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        channels = len(raw) // (w * h)
        if channels == 3:
            arr = raw.reshape((h, w, 3))
            pil = Image.fromarray(arr, mode="RGB")
        elif channels == 4:
            arr = raw.reshape((h, w, 4))[:, :, :3]
            pil = Image.fromarray(arr, mode="RGB")
        else:
            return

        out = io.BytesIO()
        pil.save(out, format="JPEG", quality=args.quality)
        sim_us = int(msg.header.stamp.sec) * 1_000_000 + int(msg.header.stamp.nsec) // 1_000
        if sim_us == 0:
            sim_us = int(time.time() * 1_000_000)
        buf.update(out.getvalue(), sim_us, w, h)

    if not node.subscribe(GzImage, args.topic, on_image):
        print(f"ERROR: Failed to subscribe to Gazebo topic {args.topic}", file=sys.stderr)
        sys.exit(1)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(buf))
    server.daemon_threads = True

    def handle_sig(_signum, _frame) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    print(f"Camera relay subscribed to {args.topic} -> http://{args.host}:{args.port}/stream.mjpeg", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
