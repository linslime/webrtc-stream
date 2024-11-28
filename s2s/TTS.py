from aip import AipSpeech

""" 你的 APPID AK SK """
APP_ID = '116326641'
API_KEY = 'pXxzzKwORSnRqLv16MPKzCbt'
SECRET_KEY = 'd3WH7vVG8UG2VbfsZDRcMQryLifOYFrZ'

client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)


def text_to_speech(text):
    result = client.synthesis(text, 'zh', 1, {
    'vol': 5,
    'per': 1,
    'spd': 7,
    })
    return result
