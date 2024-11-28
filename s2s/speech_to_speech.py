from s2s.ASR import speech_to_text
from s2s.LLM import chat
from s2s.TTS import text_to_speech
import time


def speech_to_speech(speech):
	text = speech_to_text(speech)
	response = chat(text)
	result = text_to_speech(response)
	file_name = './result' + str(time.time()) + '.wav'
	if not isinstance(result, dict):
		with open(file_name, 'wb') as f:
			f.write(result)
	return file_name


if __name__ == '__main__':
	speech = '/home/linslime/code/CleanS2S/1718090483_普通话_标准女声.wav'
	audio = speech_to_speech(speech)

	pass

	