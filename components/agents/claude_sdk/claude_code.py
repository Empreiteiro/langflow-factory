from langflow.custom import Component
from langflow.io import StrInput, Output, SecretStrInput
from langflow.schema import Data
import subprocess
import os
import tempfile
import platform


class ClaudeTerminalComponent(Component):
    display_name = "Claude Terminal"
    description = (
        "Executes Claude CLI commands in a new terminal to avoid conflicts with Langflow. "
        "This component opens a separate terminal process, runs the command, and returns the result."
    )
    icon = "bot"
    name = "ClaudeTerminalComponent"
    beta = True

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Claude API Key",
            info="Your Claude API key for authentication.",
            required=True,
        ),
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="The text or instructions to send to Claude.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Claude Response", method="run_terminal_query"),
    ]

    field_order = [
        "api_key",
        "prompt",
    ]

    def _execute_in_new_terminal(self, command, env_vars=None):
        """Execute a command in a new terminal and return the result."""
        try:
            # Prepare environment variables
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Determine command based on operating system
            if platform.system() == "Windows":
                # Windows: use cmd /c to execute in new process
                cmd = ["cmd", "/c", command]
            else:
                # Linux/Mac: use bash -c
                cmd = ["bash", "-c", command]
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes timeout
                env=env
            )
            
            return result
            
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

    def run_terminal_query(self) -> Data:
        """Executes the prompt using Claude CLI in a new terminal."""
        
        try:
            # Prepare CLI command
            claude_command = f'claude -p "{self.prompt}"'
            
            # Execute in new terminal
            env_vars = {"ANTHROPIC_API_KEY": self.api_key}
            result = self._execute_in_new_terminal(claude_command, env_vars)
            
            if result is None:
                error_msg = "Command timed out or failed to execute in new terminal"
                self.status = error_msg
                return Data(data={"error": error_msg})
            
            if result.returncode == 0:
                # Success
                response_text = result.stdout.strip()
                self.status = "Query executed successfully in new terminal."
                return Data(data={"text": response_text})
            else:
                # Error
                error_msg = f"CLI error in new terminal: {result.stderr}"
                
                # Specific error handling
                if "not authenticated" in result.stderr.lower():
                    error_msg = (
                        "Authentication failed in new terminal.\n\n"
                        "SOLUTION:\n"
                        "1. Verify your API key is correct\n"
                        "2. Check API key permissions\n"
                        "3. Get a new API key from https://console.anthropic.com/\n\n"
                        f"Error: {result.stderr}"
                    )
                elif "not found" in result.stderr.lower() or "command not found" in result.stderr.lower():
                    error_msg = (
                        "Claude CLI not found in new terminal.\n\n"
                        "SOLUTION:\n"
                        "1. Install: npm install -g @anthropic-ai/claude-agent-sdk\n"
                        "2. Verify: claude --version\n"
                        "3. Test: claude -p 'test'\n\n"
                        f"Error: {result.stderr}"
                    )
                
                self.status = error_msg
                return Data(data={"error": error_msg})
                
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg})
