import argparse
import asyncio
import json
import logging
import os
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)
from aiortc.contrib.media import MediaRecorder
from av import VideoFrame
ROOT = os.path.dirname(__file__)


relay = None
webcam = None


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
    
    player = MediaRecorder('./file.mp4')
    
    @pc.on("track")
    def on_track(track):
        print("======= received track: ", track)
        if track.kind == "video":
            t = FaceSwapper(track)
            player.addTrack(t)
            pc.addTrack(t)
    
    await pc.setRemoteDescription(offer)
    await player.start()
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


class FaceSwapper(VideoStreamTrack):
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        timestamp, video_timestamp_base = await self.next_timestamp()
        frame = await self.track.recv()
        data = frame.to_ndarray(format="bgr24")
        print(data.shape)
        print(data)
        
        frame.pts = timestamp
        frame.time_base = video_timestamp_base
        return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port)
