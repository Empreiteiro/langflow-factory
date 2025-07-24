from langflow.custom import Component
from langflow.io import StrInput, FileInput, SecretStrInput, Output
from langflow.schema import Data
import os
import tempfile
import requests
import subprocess
from openai import OpenAI
import base64
import shutil

class VideoToTextGPT4V(Component):
    display_name = "OpenAI VTT"
    description = "Converts a video into a textual description using GPT-4 with Vision. Accepts either a video URL or uploaded video file."
    icon = "OpenAI"
    name = "VideoToTextGPT4V"
    beta = True

    inputs = [
        StrInput(
            name="video_url",
            display_name="Video URL",
            info="Direct link to a video file (mp4, avi, mov, mkv, webm).",
            required=False,
        ),
        FileInput(
            name="video_file",
            display_name="Upload Video File",
            info="Upload a video file directly.",
            file_types=["mp4", "avi", "mov", "mkv", "webm", "flv", "wmv"],
            required=False,
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name="OpenAI API Key",
            required=True,
            info="Your OpenAI API key with GPT-4V access."
        ),
    ]

    outputs = [
        Output(name="summary", display_name="Video Summary", method="generate_summary"),
    ]

    field_order = ["video_url", "video_file", "openai_api_key"]

    def check_ffmpeg_availability(self) -> bool:
        """Check if ffmpeg is available in the system."""
        try:
            subprocess.run(["ffmpeg", "-version"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def generate_summary(self) -> Data:
        try:
            # Check ffmpeg availability first
            if not self.check_ffmpeg_availability():
                error_msg = """FFmpeg is required but not found on your system.
                
Please install FFmpeg:

Windows:
1. Download from https://ffmpeg.org/download.html
2. Add to PATH environment variable
OR use: winget install FFmpeg

Mac:
brew install ffmpeg

Linux:
sudo apt update && sudo apt install ffmpeg
OR
sudo yum install ffmpeg

After installation, restart your application."""
                
                self.log("FFmpeg not found. Installation required.")
                return Data(data={"error": error_msg})
            
            # Validate that at least one input is provided
            if not self.video_url and not self.video_file:
                return Data(data={"error": "Please provide either a video URL or upload a video file."})
            
            # Get API key value (handle both string and secret object)
            api_key = self.openai_api_key
            if hasattr(api_key, 'get_secret_value'):
                api_key = api_key.get_secret_value()
            
            if not api_key:
                return Data(data={"error": "OpenAI API key is required."})
            
            # Determine video source and get video path
            if self.video_file:
                self.status = "Processing uploaded video file..."
                video_path = self.prepare_uploaded_video(self.video_file)
            else:
                self.status = "Downloading and processing video from URL..."
                video_path = self.download_video(self.video_url)
            
            # Extract frames and analyze with GPT-4V
            self.status = "Extracting frames from video..."
            frames, frames_dir = self.extract_frames(video_path, num_frames=3)
            
            self.status = "Analyzing video content with GPT-4V..."
            summary = self.query_gpt4v(frames, api_key)
            
            # Cleanup temporary files
            cleanup_paths = [video_path, frames_dir] if frames_dir else [video_path] + frames
            self.cleanup(cleanup_paths)
            
            self.status = "Video analysis completed successfully!"
            return Data(data={"text": summary, "summary": summary})
            
        except Exception as e:
            self.status = f"Error: {str(e)}"
            self.log(f"Video processing error: {str(e)}")
            return Data(data={"error": str(e)})

    def prepare_uploaded_video(self, video_file: str) -> str:
        """Copy uploaded video file to a temporary location for processing."""
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Uploaded video file not found: {video_file}")
        
        # Get file extension from original file
        _, ext = os.path.splitext(video_file)
        if not ext:
            ext = ".mp4"  # Default extension
            
        # Create temporary file with same extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            shutil.copy2(video_file, tmp_file.name)
            return tmp_file.name

    def download_video(self, url: str) -> str:
        """Download video from URL to a temporary file."""
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Try to get file extension from URL or Content-Type
        ext = ".mp4"  # Default
        if url.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv')):
            ext = os.path.splitext(url.lower())[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name

    def extract_frames(self, video_path: str, num_frames: int = 3) -> tuple[list[str], str]:
        """Extract frames from video and return frame paths and temp directory."""
        tmp_dir = tempfile.mkdtemp()
        output_pattern = os.path.join(tmp_dir, "frame_%03d.jpg")
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{max(1, num_frames)}",  # Distribute frames across video duration
            "-vframes", str(num_frames),
            output_pattern,
            "-hide_banner", "-loglevel", "error"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            frame_files = [os.path.join(tmp_dir, f) for f in sorted(os.listdir(tmp_dir)) if f.endswith(".jpg")]
            return frame_files, tmp_dir
        except subprocess.CalledProcessError as e:
            # Clean up on error
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            raise RuntimeError(f"Failed to extract frames from video. FFmpeg error: {e}")

    def query_gpt4v(self, image_paths: list[str], api_key: str) -> str:
        client = OpenAI(api_key=api_key)
        image_data = []
        for path in image_paths:
            with open(path, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode("utf-8")
                image_data.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_img}"
                    }
                })
        prompt = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyze these frames from a video and provide a comprehensive description of the content, including: the main subjects/objects, setting/environment, actions or events taking place, visual style, and any notable details. Create a coherent narrative that connects the frames as part of a single video sequence."
                        },
                        *image_data
                    ]
                }
            ],
            "max_tokens": 800
        }
        response = client.chat.completions.create(**prompt)
        return response.choices[0].message.content.strip()

    def cleanup(self, paths: list[str]):
        """Clean up temporary files and directories."""
        for p in paths:
            try:
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    # Get the directory path for cleanup
                    frame_dir = os.path.dirname(p) if os.path.isfile(p) else p
                    if os.path.exists(frame_dir):
                        shutil.rmtree(frame_dir)
            except (OSError, FileNotFoundError) as e:
                # Log but don't fail on cleanup errors
                self.log(f"Warning: Could not clean up {p}: {e}")
