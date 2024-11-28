import argparse
import asyncio
import json
import logging
import os
import traceback
from s2s import speech_to_speech
from s2s_processor import s2s_processor

import numpy as np
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    AudioStreamTrack,
)
from aiortc.contrib.media import MediaRecorder, MediaPlayer, MediaStreamTrack, MediaRecorderContext, MediaStreamError
from av import VideoFrame
from av import AudioFrame
import librosa
import av


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
    
    processor = s2s_processor()
    
    @pc.on("track")
    def on_track(track):
        print("======= received track: ", track)
        if track.kind == "video":
            vedio = VedioSender(track)
            pc.addTrack(vedio)
        if track.kind == "audio":
            processor.addTrack(track)
            pc.addTrack(processor)
    
    await pc.setRemoteDescription(offer)
    await processor.start()
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


class VedioSender(VideoStreamTrack):
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        timestamp, video_timestamp_base = await self.next_timestamp()
        frame = await self.track.recv()
        frame.pts = timestamp
        frame.time_base = video_timestamp_base
        return frame


class AudioSender(AudioStreamTrack):
    kind = "audio"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        return frame


class AudioRecorder:
    Volume_Threshold = 20
    def __init__(self, file, format=None, options=None):
        self.__container = av.open(file=file, format=format, mode="w", options=options)
        self.__tracks = {}
        self.__state = 0
        self.__time = -1
    
    def addTrack(self, track):
        """
        Add a track to be recorded.

        :param track: A :class:`aiortc.MediaStreamTrack`.
        """
        if track.kind == "audio":
            if self.__container.format.name in ("wav", "alsa", "pulse"):
                codec_name = "pcm_s16le"
            elif self.__container.format.name == "mp3":
                codec_name = "mp3"
            else:
                codec_name = "aac"
            stream = self.__container.add_stream(codec_name)
        else:
            if self.__container.format.name == "image2":
                stream = self.__container.add_stream("png", rate=30)
                stream.pix_fmt = "rgb24"
            else:
                stream = self.__container.add_stream("libx264", rate=30)
                stream.pix_fmt = "yuv420p"
        self.__tracks[track] = MediaRecorderContext(stream)
    
    async def start(self):
        """
        Start recording.
        """
        for track, context in self.__tracks.items():
            if context.task is None:
                context.task = asyncio.ensure_future(self.__run_track(track, context))
    
    async def stop(self):
        """
        Stop recording.
        """
        if self.__container:
            for track, context in self.__tracks.items():
                if context.task is not None:
                    context.task.cancel()
                    context.task = None
                    for packet in context.stream.encode(None):
                        self.__container.mux(packet)
            self.__tracks = {}
            
            if self.__container:
                self.__container.close()
                self.__container = None
    
    async def __run_track(self, track: MediaStreamTrack, context: MediaRecorderContext):
        while True:
            try:
                frame = await track.recv()
                max = np.absolute(frame.to_ndarray()).max()
                if self.__state == 0:
                    if max >= AudioRecorder.Volume_Threshold:
                        self.__state = 1
                    else:
                        continue
                elif self.__state == 1:
                    if max >= AudioRecorder.Volume_Threshold:
                        pass
                    else:
                        self.__state = 2
                        self.__time = frame.pts
                elif self.__state == 2:
                    if max >= AudioRecorder.Volume_Threshold:
                        self.__state = 1
                        self.__time = -1
                    else:
                        if frame.pts - self.__time > 10000:
                            return
                        else:
                            pass
            except MediaStreamError:
                return

            if not context.started:
                # adjust the output size to match the first frame
                if isinstance(frame, VideoFrame):
                    context.stream.width = frame.width
                    context.stream.height = frame.height
                context.started = True

            for packet in context.stream.encode(frame):
                self.__container.mux(packet)


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
