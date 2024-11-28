import av
from aiortc.contrib.media import MediaRecorderContext, MediaPlayer, MediaStreamError
import asyncio
import numpy as np
import time
from s2s import speech_to_speech
import os
from aiortc import AudioStreamTrack
import threading


class AudioRecorder:
	
	def __init__(self, file, format=None, options=None):
		self.__container = av.open(file=file, format=format, mode="w", options=options)

	def start(self):
		codec_name = "pcm_s16le"
		stream = self.__container.add_stream(codec_name)
		self.__media_recorder_context = MediaRecorderContext(stream)
	
	def stop(self):
		if self.__container:
			if self.__media_recorder_context.task is not None:
				self.__media_recorder_context.task.cancel()
				self.__media_recorder_context.task = None
				for packet in self.__media_recorder_context.stream.encode(None):
					self.__container.mux(packet)
			if self.__container:
				self.__container.close()
				self.__container = None
				
	def add_frame(self, frame):
		for packet in self.__media_recorder_context.stream.encode(frame):
			self.__container.mux(packet)


class AudioTrack(AudioStreamTrack):
	kind = "audio"

	def __init__(self, queue):
		super().__init__()
		self.__queue = queue
	
	async def recv(self):
		frame = await self.__queue.get()
		return frame


class s2s_processor(AudioStreamTrack):
	kind = "audio"
	Volume_Threshold = 5000
	
	def __init__(self):
		super().__init__()
		self.__task_queue = asyncio.Queue()
		self.__result_queue = asyncio.Queue()
		self.__frame_queue = asyncio.Queue()
		self.__lock = threading.Lock()
		self.__lock.acquire()
		
	async def start(self):
		self.__lock.acquire()
		asyncio.ensure_future(self.__receive_audio())
		# asyncio.ensure_future(self.__sp2sp())
		# asyncio.ensure_future(self.__sp2frame())
	
	def addTrack(self, track):
		self.__track = track
		time.sleep(2)
		self.__lock.release()
	
	async def __receive_audio(self):
		state = 0
		true_flag = -1
		false_flag = -1
		current_audio_recorder = None
		file_name = None
		while True:
			frame = await self.__track.recv()
			max = np.absolute(frame.to_ndarray()).max()
			print(max, state)
			if state == 0:
				if max >= s2s_processor.Volume_Threshold:
					file_name = './task' + str(time.time()) + '.wav'
					current_audio_recorder = AudioRecorder(file_name)
					current_audio_recorder.start()
					current_audio_recorder.add_frame(frame)
					true_flag = frame.pts
					state = 1
				else:
					continue
			elif state == 1:
				current_audio_recorder.add_frame(frame)
				if max >= s2s_processor.Volume_Threshold:
					pass
				else:
					state = 2
					false_flag = frame.pts
			elif state == 2:
				current_audio_recorder.add_frame(frame)
				if max >= s2s_processor.Volume_Threshold:
					state = 1
					false_flag = -1
				else:
					if frame.pts - false_flag > 10000:
						if frame.pts - true_flag > 30000:
							current_audio_recorder.stop()
							result_file_path = speech_to_speech(file_name)
							result_audio = MediaPlayer(result_file_path)
							while True:
								try:
									frame = await result_audio.audio.recv()
								except MediaStreamError:
									break
								await self.__frame_queue.put(frame)
							while True:
								if self.__frame_queue.qsize() == 1:
									await self.__frame_queue.get()
									break
						state = 0
						false_flag = -1
					else:
						pass
		print("haha")
	async def __sp2sp(self):
		while True:
			task_file_path = await self.__task_queue.get()
			result_file_path = speech_to_speech(task_file_path)
			await self.__result_queue.put(result_file_path)
			os.remove(task_file_path)
	
	async def __sp2frame(self):
		while True:
			result_file_path = await self.__result_queue.get()
			result_audio = MediaPlayer(result_file_path)
			while True:
				try:
					frame = await result_audio.audio.recv()
				except MediaStreamError:
					break
				await self.__frame_queue.put(frame)
				
	async def recv(self):
		frame = await self.__frame_queue.get()
		return frame
