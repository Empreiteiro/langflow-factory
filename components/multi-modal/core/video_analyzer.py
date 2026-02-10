"""
Video Analyzer – analyzes video from file or URL.

Supports direct video URLs, YouTube, and Google Drive (same logic as multi-modal Input).
Optional: yt-dlp for YouTube; FFmpeg required for frame extraction.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.parse import urlparse

import requests

from lfx.custom import Component
from lfx.io import (
    DropdownInput,
    FileInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
    TabInput,
)
from lfx.schema import Data
from lfx.schema.message import Message


class ModelVideoAnalyzer(Component):
    display_name = "Video Analyzer"
    description = "Analyzes videos by extracting frames and running image analysis."
    icon = "video"
    name = "ModelVideoAnalyzerComponent"

    MODEL_PROVIDERS_LIST = [
        "OpenAI",
        "OpenAI-Compatible",
    ]

    VIDEO_MODELS_BY_PROVIDER = {
        "OpenAI": ["gpt-4o", "gpt-4o-mini"],
        "OpenAI-Compatible": ["gpt-4o", "gpt-4o-mini"],
    }

    BASE_URL_BY_PROVIDER = {
        "OpenAI": "https://api.openai.com/v1",
        "OpenAI-Compatible": "https://api.openai.com/v1",
    }

    inputs = [
        DropdownInput(
            name="provider",
            display_name="Model Provider",
            info="Select the provider with video analysis capabilities.",
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            info="Select the model.",
            options=[*VIDEO_MODELS_BY_PROVIDER["OpenAI"]],
            value="gpt-4o-mini",
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Model Provider API key",
            required=True,
            real_time_refresh=True,
            advanced=True,
        ),
        StrInput(
            name="base_url",
            display_name="API Base URL",
            info="OpenAI-compatible base URL (e.g. https://api.openai.com/v1)",
            value="https://api.openai.com/v1",
            advanced=True,
            show=False,
        ),
        TabInput(
            name="video_source",
            display_name="Video Source",
            options=["File", "URL"],
            value="File",
            info="Load video from uploaded file or from a URL (direct, YouTube, Google Drive).",
            real_time_refresh=True,
        ),
        FileInput(
            name="video_file",
            display_name="File",
            file_types=["mp4", "mpeg", "webm", "avi", "mov", "mkv", "flv", "wmv"],
            info="Upload a video file for analysis.",
            required=False,
            show=True,
        ),
        MessageTextInput(
            name="video_url",
            display_name="URL",
            info="URL of the video (direct link, YouTube, or Google Drive).",
            required=False,
            show=False,
        ),
        IntInput(
            name="num_frames",
            display_name="Frames",
            info="Number of frames to extract for analysis.",
            value=3,
            advanced=True,
        ),
        MessageTextInput(
            name="prompt",
            display_name="Prompt",
            info="Instruction for analysis.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="analysis_data",
            display_name="Analysis Data",
            method="analyze_video",
        ),
        Output(
            name="analysis_text",
            display_name="Analysis Text",
            method="get_analysis_text",
        ),
    ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name == "provider":
            provider = field_value or build_config.get("provider", {}).get("value")
            model_options = self.VIDEO_MODELS_BY_PROVIDER.get(provider, ["gpt-4o-mini"])

            if "model" in build_config:
                build_config["model"]["options"] = model_options
                current_value = build_config["model"].get("value")
                if current_value not in model_options:
                    build_config["model"]["value"] = model_options[0]

            if "base_url" in build_config:
                build_config["base_url"]["value"] = self.BASE_URL_BY_PROVIDER.get(
                    provider, "https://api.openai.com/v1"
                )
                build_config["base_url"]["show"] = provider == "OpenAI-Compatible"

        elif field_name == "video_source":
            source = field_value or build_config.get("video_source", {}).get("value") or "File"
            if "video_file" in build_config:
                build_config["video_file"]["show"] = source == "File"
            if "video_url" in build_config:
                build_config["video_url"]["show"] = source == "URL"

        return build_config

    def _normalize_model(self, model_value: str) -> str:
        if not model_value:
            return "gpt-4o-mini"
        if ":" in model_value:
            return model_value.split(":", 1)[1].strip() or model_value
        return model_value.strip()

    def _build_openai_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _download_video_from_url(self, url: str) -> tuple[str, list[str]]:
        """Download video from URL (direct, YouTube, Google Drive). Returns (local_path, paths_to_cleanup)."""
        parsed = urlparse(url)
        if not parsed.scheme:
            raise ValueError("Invalid URL: missing scheme (http/https)")

        self.log(f"Downloading video from URL: {url}")

        if "youtube.com" in url or "youtu.be" in url:
            self.log("Detected YouTube URL")
            try:
                return self._download_youtube_video(url)
            except ImportError:
                self.log("yt-dlp not available, trying direct download")
                path = self._download_direct_url(url)
                return path, [path]
            except Exception as e:
                self.log(f"YouTube download failed: {e}, trying direct download")
                path = self._download_direct_url(url)
                return path, [path]
        if "drive.google.com" in url:
            self.log("Detected Google Drive URL")
            path = self._download_google_drive_video(url)
            return path, [path]
        path = self._download_direct_url(url)
        return path, [path]

    def _download_direct_url(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        ext = ".mp4" if "video" in content_type else ".mp4"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        return temp_file.name

    def _download_youtube_video(self, url: str) -> tuple[str, list[str]]:
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("yt-dlp is required for YouTube URLs. Install with: pip install yt-dlp")

        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            "format": "best[height<=1080]/best[ext=mp4]/best",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        all_files = []
        for root, _dirs, filenames in os.walk(temp_dir):
            for f in filenames:
                all_files.append(os.path.join(root, f))
        if not all_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("No file downloaded from YouTube.")
        path = all_files[0]
        return path, [path, temp_dir]

    def _download_google_drive_video(self, url: str) -> str:
        if "/d/" in url:
            file_id = url.split("/d/")[1].split("/")[0]
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        else:
            raise ValueError("Could not extract file ID from Google Drive URL")
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        return temp_file.name

    def _get_video_path(self) -> tuple[str | None, str | None, list[str]]:
        """Returns (video_path, error_message, cleanup_paths). cleanup_paths are to delete after analysis."""
        source = getattr(self, "video_source", "File") or "File"

        if source == "File":
            if not self.video_file:
                return None, "Video file is required.", []
            video_path = self.video_file
            if isinstance(video_path, list):
                video_path = video_path[0] if video_path else None
            if not video_path or not os.path.exists(video_path):
                return None, f"Video file not found at {video_path}", []
            if os.path.getsize(video_path) == 0:
                return None, "Video file is empty.", []
            return video_path, None, []

        if source == "URL":
            url = getattr(self, "video_url", "") or ""
            if hasattr(url, "text"):
                url = url.text
            url = str(url).strip()
            if not url:
                return None, "Video URL is required.", []
            try:
                path, cleanup = self._download_video_from_url(url)
                return path, None, cleanup
            except Exception as e:
                return None, f"Failed to download video: {e}", []

        return None, "Video file or video URL is required.", []

    def _get_api_key(self) -> tuple[str | None, str | None]:
        if not self.api_key:
            return None, "API key is required."

        api_key = self.api_key.get_secret_value() if hasattr(self.api_key, "get_secret_value") else str(self.api_key)
        api_key = api_key.strip()
        if not api_key:
            return None, "A valid API key is required."

        return api_key, None

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _extract_frames(self, video_path: str, num_frames: int) -> tuple[list[str], str]:
        tmp_dir = tempfile.mkdtemp()

        try:
            probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
            subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            raise RuntimeError(f"Invalid or corrupted video file. FFprobe error: {e.stderr}") from e

        strategies = [
            {
                "name": "Standard extraction",
                "cmd": [
                    "ffmpeg", "-i", video_path,
                    "-vf", f"fps=1/{max(1, num_frames)}",
                    "-vframes", str(num_frames),
                    os.path.join(tmp_dir, "frame_%03d.jpg"),
                    "-hide_banner", "-loglevel", "error",
                ],
            },
            {
                "name": "Timestamp-based extraction",
                "cmd": [
                    "ffmpeg", "-i", video_path,
                    "-vf", "select='eq(pict_type,I)'",
                    "-vsync", "vfr",
                    "-vframes", str(num_frames),
                    os.path.join(tmp_dir, "frame_%03d.jpg"),
                    "-hide_banner", "-loglevel", "error",
                ],
            },
            {
                "name": "Interval-based extraction",
                "cmd": [
                    "ffmpeg", "-i", video_path,
                    "-vf", "select='not(mod(n,30))'",
                    "-vframes", str(num_frames),
                    os.path.join(tmp_dir, "frame_%03d.jpg"),
                    "-hide_banner", "-loglevel", "error",
                ],
            },
            {
                "name": "Simple extraction",
                "cmd": [
                    "ffmpeg", "-i", video_path,
                    "-vframes", str(num_frames),
                    os.path.join(tmp_dir, "frame_%03d.jpg"),
                    "-hide_banner", "-loglevel", "error",
                ],
            },
        ]

        for strategy in strategies:
            try:
                subprocess.run(strategy["cmd"], check=True, capture_output=True, text=True)
                frame_files = [
                    os.path.join(tmp_dir, f)
                    for f in sorted(os.listdir(tmp_dir))
                    if f.endswith(".jpg")
                ]
                if frame_files:
                    return frame_files, tmp_dir
            except subprocess.CalledProcessError:
                continue

        try:
            simple_cmd = [
                "ffmpeg", "-i", video_path,
                "-vframes", "1",
                os.path.join(tmp_dir, "single_frame.jpg"),
                "-hide_banner", "-loglevel", "error",
            ]
            subprocess.run(simple_cmd, check=True, capture_output=True, text=True)
            single_frame = os.path.join(tmp_dir, "single_frame.jpg")
            if os.path.exists(single_frame):
                return [single_frame], tmp_dir
        except subprocess.CalledProcessError:
            pass

        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        raise RuntimeError("Failed to extract any frames from video.")

    def _build_openai_message(self, frame_paths: list[str], prompt: str) -> dict[str, Any]:
        image_data: list[dict[str, Any]] = []
        for path in frame_paths:
            with open(path, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode("utf-8")
            image_data.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
            })

        prompt_text = (
            prompt.strip()
            if prompt
            else "Analyze these frames from a video and provide a concise description of the content and events."
        )

        return {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                *image_data,
            ],
        }

    def _analyze_openai(self, api_key: str, video_path: str, model: str) -> dict:
        if not self._check_ffmpeg():
            return {"error": "FFmpeg is required but not available in PATH."}

        num_frames = getattr(self, "num_frames", 3) or 3
        prompt = getattr(self, "prompt", "") or ""

        frames: list[str] = []
        frames_dir = ""
        try:
            frames, frames_dir = self._extract_frames(video_path, int(num_frames))
            message = self._build_openai_message(frames, prompt)
            url = self._build_openai_url(getattr(self, "base_url", "https://api.openai.com/v1"))
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [message],
                "max_tokens": 800,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                try:
                    text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    return {"error": "OpenAI response missing content."}
                return {
                    "text": text,
                    "provider": "OpenAI",
                    "model": model,
                    "frames_used": len(frames),
                }

            return {"error": f"API Error {response.status_code}: {response.text}"}
        finally:
            for path in frames:
                try:
                    os.remove(path)
                except OSError:
                    pass
            if frames_dir and os.path.isdir(frames_dir):
                shutil.rmtree(frames_dir, ignore_errors=True)

    def _analyze_internal(self) -> dict:
        video_path, video_error, cleanup_paths = self._get_video_path()
        if video_error:
            return {"error": video_error}

        try:
            api_key, api_error = self._get_api_key()
            if api_error:
                return {"error": api_error}

            provider = getattr(self, "provider", "OpenAI") or "OpenAI"
            model = self._normalize_model(getattr(self, "model", "gpt-4o-mini"))

            if provider in ("OpenAI", "OpenAI-Compatible"):
                return self._analyze_openai(api_key, video_path, model)

            return {"error": f"Unsupported provider: {provider}"}
        finally:
            for p in cleanup_paths:
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                    elif os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                except OSError:
                    pass

    def analyze_video(self) -> Data:
        result = self._analyze_internal()
        if "error" in result:
            return Data(data={"error": result["error"]})
        return Data(data=result)

    def get_analysis_text(self) -> Message:
        result = self._analyze_internal()
        if "error" in result:
            return Message(text=f"Error: {result['error']}")
        return Message(text=result.get("text", ""))
