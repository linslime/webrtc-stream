import whisper


model = whisper.load_model(name='base', device='cuda')


def speech_to_text(speech):
	result = model.transcribe(speech, language='zh')
	return result["text"]


if __name__ == '__main__':
	result = speech_to_text("/home/linslime/code/CleanS2S/1718090483_普通话_标准女声.wav", model)
	print(result)
