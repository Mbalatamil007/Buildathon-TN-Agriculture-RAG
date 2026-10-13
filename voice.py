from config import validate_api_keys
from openai import OpenAI

def transcribe_audio(audio, language):
    validate_api_keys()
    if audio.size > 20 * 1024 * 1024:
        raise ValueError('Record a shorter question (under 20 MB).')
    return OpenAI(timeout=90, max_retries=2).audio.transcriptions.create(
        model='whisper-1', file=('question.wav', audio.getvalue(), 'audio/wav'),
        **({'language': 'ta'} if language == 'Tamil' else {'language': 'en'} if language == 'English' else {})).text

def read_aloud(text):
    # AI-generated voice. Tamil quality depends on the speech model.
    response = OpenAI(timeout=90, max_retries=2).audio.speech.create(
        model='tts-1', voice='alloy', input=text[:4000], response_format='mp3')
    return response.read()
