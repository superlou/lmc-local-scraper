import wave

from google import genai
from google.genai.types import PrebuiltVoiceConfig, SpeechConfig, VoiceConfig


class GeminiSpeechClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def generate_audio(self, dialogue: str, voice: str, output_filename: str):
        config = genai.types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        )
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-tts", contents=dialogue, config=config
        )

        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        save_data_to_wave_file(pcm_data, output_filename)


def save_data_to_wave_file(
    pcm_data, filename: str, channels=1, rate=24000, sample_width=2
):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
