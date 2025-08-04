import subprocess
import os
import sys
from langflow.custom import Component
from langflow.inputs import StrInput, DropdownInput
from langflow.template import Output
from langflow.schema.message import Message

class librariesComponent(Component):
    display_name = "Libraries Install"
    description = "Installs Python libraries with UV pip install in a specified virtual environment. Requires full path to the venv."
    icon = "download"
    name = "librariesComponent"

    inputs = [
        DropdownInput(
            name="operating_system",
            display_name="Operating System",
            options=["Auto-detect", "Windows", "Linux", "macOS"],
            value="Auto-detect",
            info="Select the operating system or use auto-detection.",
        ),
        StrInput(
            name="venv_path",
            display_name="Virtual Environment Path",
            info="Full path to the virtual environment (e.g., '/home/user/project/venv' or '~/langflow-app/venv').",
            required=True,
        ),
        StrInput(
            name="library_name",
            display_name="Library Name",
            info="Single library with optional version (e.g., 'requests==2.31.0').",
            required=True,

        ),
        StrInput(
            name="extra_args",
            display_name="Additional Arguments",
            info="Additional arguments separated by space (e.g., '-U --force-reinstall').",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Installation Status",
            name="status",
            method="install_library"
        ),
    ]

    def install_library(self) -> Message:
        debug_logs = []

        try:
            library_name = getattr(self, "library_name", "").strip()
            extra_args_str = getattr(self, "extra_args", "").strip()
            selected_os = getattr(self, "operating_system", "Auto-detect")
            venv_path_input = getattr(self, "venv_path", "").strip()

            extra_args = extra_args_str.split() if extra_args_str else []

            # Determine the operating system
            detected_os = self._detect_operating_system()
            target_os = detected_os if selected_os == "Auto-detect" else selected_os.lower()

            debug_logs.append(f"[DEBUG] Current user: {os.path.expanduser('~')}")
            debug_logs.append(f"[DEBUG] System platform: {sys.platform}")
            debug_logs.append(f"[DEBUG] Selected OS: {selected_os}")
            debug_logs.append(f"[DEBUG] Target OS: {target_os}")

            # Validate venv path
            if not venv_path_input:
                return Message(text="❌ Virtual Environment Path is required.")

            # Expand user path (~) if present
            venv_path = os.path.expanduser(venv_path_input)
            debug_logs.append(f"[DEBUG] Venv path (input): {venv_path_input}")
            debug_logs.append(f"[DEBUG] Venv path (expanded): {venv_path}")

            python_executable = self._get_python_executable(venv_path, target_os)

            debug_logs.append(f"[DEBUG] Venv path: {venv_path}")
            debug_logs.append(f"[DEBUG] Python executable: {python_executable}")
            debug_logs.append(f"[DEBUG] Extra arguments: {extra_args}")

            if not os.path.exists(python_executable):
                error_message = [
                    f"❌ Python not found in virtual environment:\n`{python_executable}`",
                    f"Check if the virtual environment exists at: {venv_path}",
                    f"Expected Python executable: {python_executable}",
                    f"Tips:",
                    f"  - Verify the path is correct: {venv_path_input}",
                    f"  - Make sure the virtual environment was created properly",
                    f"  - Check if Python is installed in the venv",
                    f"  - Example valid paths: '/home/user/project/venv', '~/langflow-app/venv'"
                ]
                return Message(text="\n".join(debug_logs + error_message))

            if not library_name:
                debug_logs.append("❌ No library name provided.")
                return Message(text="\n".join(debug_logs))

            debug_logs.append(f"[DEBUG] Library to install: {library_name}")

            result = self._install_with_uv(python_executable, [library_name], extra_args, target_os)
            debug_logs.append(f"[DEBUG] Installation result:\n{result.text}")

            return Message(text="\n".join(debug_logs + [result.text]))

        except Exception as e:
            debug_logs.append(f"[FATAL ERROR] {str(e)}")
            return Message(text="\n".join(debug_logs))

    def _detect_operating_system(self) -> str:
        """Detect the current operating system."""
        if sys.platform.startswith("win"):
            return "windows"
        elif sys.platform.startswith("darwin"):
            return "macos"
        elif sys.platform.startswith("linux"):
            return "linux"
        else:
            return "unknown"

    def _get_python_executable(self, venv_path: str, target_os: str) -> str:
        """Get the Python executable path based on the target OS."""
        if target_os == "windows":
            executable_paths = [
                os.path.join(venv_path, "Scripts", "python.exe"),
                os.path.join(venv_path, "bin", "python.exe"),
                os.path.join(venv_path, "Scripts", "python"),
            ]
        else:  # linux and macos
            executable_paths = [
                os.path.join(venv_path, "bin", "python"),
                os.path.join(venv_path, "bin", "python3"),
                os.path.join(venv_path, "Scripts", "python"),
            ]
        
        # Return the first existing executable or the default one
        for exe_path in executable_paths:
            if os.path.exists(exe_path):
                return exe_path
        
        # Return default path if none found
        return executable_paths[0]

    def _install_with_uv(self, python_path: str, libs: list[str], extra_args: list[str], target_os: str) -> Message:
        """Install libraries with UV pip, with OS-specific handling."""
        try:
            # Build command with OS-specific considerations
            cmd = [python_path, "-m", "uv", "pip", "install", *libs, *extra_args]
            
            # OS-specific environment variables
            env = os.environ.copy()
            if target_os == "windows":
                # Ensure UTF-8 encoding on Windows
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                timeout=300  # 5 minute timeout
            )
            return Message(text=f"✅ UV installation completed on {target_os}.\nSTDOUT:\n{result.stdout}")
        except subprocess.TimeoutExpired:
            return Message(text=f"❌ Installation timed out after 5 minutes on {target_os}.")
        except subprocess.CalledProcessError as e:
            error_msg = f"❌ Failed to install with UV on {target_os}.\nSTDERR:\n{e.stderr}"
            if e.stdout:
                error_msg += f"\nSTDOUT:\n{e.stdout}"
            
            # Add OS-specific troubleshooting hints
            if target_os == "windows" and "permission" in e.stderr.lower():
                error_msg += "\n\n💡 Windows Tip: Try running as administrator or check antivirus settings."
            elif target_os == "linux" and "permission" in e.stderr.lower():
                error_msg += "\n\n💡 Linux Tip: Check file permissions and ensure you have write access to the venv."
            elif target_os == "macos" and "permission" in e.stderr.lower():
                error_msg += "\n\n💡 macOS Tip: Check System Integrity Protection (SIP) settings if needed."
            
            return Message(text=error_msg)
        except Exception as e:
            return Message(text=f"❌ Unexpected error during installation on {target_os}: {str(e)}")
