from langflow.custom import Component
from langflow.io import StrInput, DropdownInput, SecretStrInput, Output
from langflow.schema import Data

from google.cloud import texttospeech
import os


class GoogleTextToSpeechComponent(Component):
    display_name = "Google TTS"
    description = "Converte texto em fala usando a API do Google Text-to-Speech."
    icon = "volume-high"
    name = "GoogleTextToSpeech"

    field_order = ["api_key_path", "text", "language_code", "voice_name", "audio_encoding"]

    inputs = [
        SecretStrInput(
            name="api_key_path",
            display_name="Caminho para credenciais JSON",
            info="Caminho para o arquivo de credenciais da conta de serviço do Google Cloud.",
            required=True
        ),
        StrInput(
            name="text",
            display_name="Texto",
            info="Texto a ser convertido em fala.",
            required=True
        ),
        DropdownInput(
            name="language_code",
            display_name="Código do Idioma",
            options=["pt-BR", "en-US", "es-ES"],
            value="pt-BR",
            info="Código do idioma e região."
        ),
        DropdownInput(
            name="voice_name",
            display_name="Nome da Voz",
            options=["pt-BR-Wavenet-A", "pt-BR-Wavenet-B", "en-US-Wavenet-D"],
            value="pt-BR-Wavenet-A",
            info="Nome da voz desejada."
        ),
        DropdownInput(
            name="audio_encoding",
            display_name="Formato de Áudio",
            options=["MP3", "LINEAR16", "OGG_OPUS"],
            value="MP3",
            info="Formato de saída do áudio gerado."
        ),
    ]

    outputs = [
        Output(name="audio_data", display_name="Áudio Gerado", method="generate_audio")
    ]

    def generate_audio(self) -> Data:
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.api_key_path
            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=self.text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=getattr(texttospeech.AudioEncoding, self.audio_encoding)
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            self.status = "Áudio gerado com sucesso."
            return Data(data=response.audio_content)

        except Exception as e:
            error_msg = f"Erro ao gerar áudio: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
