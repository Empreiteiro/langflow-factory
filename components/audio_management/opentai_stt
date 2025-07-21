from langflow.custom import Component
from langflow.io import FileInput, Output, StrInput
from langflow.schema import Data
import tempfile
import os

from openai import OpenAI

class OpenAIAudioToTextComponent(Component):
    display_name = "OpenAI Audio to Text"
    description = "Transcribes audio to text using OpenAI's Whisper model. Accepts a file upload or a URL."
    icon = "OpenAI"
    name = "OpenAIAudioToText"

    inputs = [
        FileInput(
            name="audio_file",
            display_name="Audio File",
            info="Upload an audio file (mp3, mp4, mpeg, mpga, wav, or webm).",
            file_types=["mp3", "mp4", "mpeg", "mpga", "wav", "webm"],
            required=True,
        ),
        StrInput(
            name="openai_api_key",
            display_name="OpenAI API Key",
            required=True,
        )
    ]

    outputs = [
        Output(name="transcription", display_name="Transcription Text", method="transcribe_audio")
    ]

    field_order = ["audio_file", "openai_api_key"]

    def transcribe_audio(self) -> Data:
        # Check for file input
        if not self.audio_file:
            return Data(text="Error: Please provide an audio file.")

        try:
            self.log(f"Audio file type: {type(self.audio_file)}")
            self.log(f"Audio file value: {self.audio_file}")
            
            # Check if the file exists (following AssemblyAI pattern)
            if not os.path.exists(self.audio_file):
                self.log(f"File not found at: {self.audio_file}")
                return Data(text=f"Error: Audio file not found at {self.audio_file}")
            
            # Use the file path directly
            audio_path = self.audio_file
            self.log(f"Using audio file path: {audio_path}")
            
            # Check file size
            file_size = os.path.getsize(audio_path)
            self.log(f"Audio file size: {file_size} bytes")
            
            if file_size == 0:
                return Data(text="Error: Audio file is empty")
            



            
            # Transcribe using OpenAI Whisper API
            client = OpenAI(api_key=self.openai_api_key)
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )



            return Data(text=transcript.text)

        except Exception as e:
            self.status = f"Transcription failed: {str(e)}"
            self.log(self.status)
            return Data(text=self.status)
