from langflow.custom import Component
from langflow.io import StrInput, Output, BoolInput
from langflow.schema import Data
import subprocess
import shutil
import os


class ClaudeCodeCLIComponent(Component):
    display_name = "Claude Code CLI"
    description = (
        "Executes queries to Claude Code via CLI. "
        "Ideal for simple questions, automations, and plain text responses."
    )
    icon = "bot"
    name = "ClaudeCodeCLI"
    beta = True

    inputs = [
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="Input text to be sent to the Claude Code CLI.",
            required=True,
        ),
        StrInput(
            name="system_prompt",
            display_name="System Prompt",
            info="Optional system prompt to configure the execution context.",
            required=False,
        ),
        StrInput(
            name="working_directory",
            display_name="Working Directory",
            info="Execution path (e.g., /home/user/project).",
            required=False,
        ),
        BoolInput(
            name="debug",
            display_name="Debug",
            info="Enables detailed logs during execution.",
            value=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Claude CLI Response", method="run_cli_query"),
    ]

    field_order = [
        "prompt",
        "system_prompt",
        "working_directory",
        "debug",
    ]

    def _check_claude_cli(self):
        """Check if Claude CLI is available and authenticated."""
        claude_path = shutil.which("claude")
        if not claude_path:
            return False, "Claude CLI not found in PATH. Install it first."

        try:
            # Check version
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, f"Claude CLI failed: {result.stderr}"

            version = result.stdout.strip() or "version unknown"
            return True, f"Claude CLI found: {version}"
        except subprocess.TimeoutExpired:
            return False, "Claude CLI check timed out"
        except Exception as e:
            return False, f"Error checking Claude CLI: {e}"

    def _execute_claude_query(self, prompt: str) -> str:
        """Execute Claude query using subprocess with proper input handling."""
        try:
            # Build the command
            cmd = ["claude"]

            # Set working directory if provided
            cwd = self.working_directory or None

            # Create environment with system prompt if provided
            env = os.environ.copy()
            if self.system_prompt:
                env["CLAUDE_SYSTEM_PROMPT"] = self.system_prompt

            if self.debug:
                self.log(f"Executing: {' '.join(cmd)}")
                self.log(f"Working directory: {cwd}")
                self.log(f"Prompt: {prompt[:100]}...")

            # Execute Claude CLI with prompt via stdin
            # Using non-interactive mode
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env
            )

            # Send the prompt and get response
            stdout, stderr = process.communicate(input=prompt, timeout=300)  # 5 min timeout

            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "Unknown error"
                if self.debug:
                    self.log(f"Claude CLI failed with code {process.returncode}: {error_msg}")
                return f"Error: {error_msg}"

            if self.debug:
                self.log(f"Response length: {len(stdout)} chars")

            return stdout.strip() or "No response from Claude."

        except subprocess.TimeoutExpired:
            return "Error: Claude CLI query timed out (5 minutes)"
        except Exception as e:
            if self.debug:
                self.log(f"Exception during execution: {type(e).__name__}: {e}")
            return f"Error executing Claude CLI: {e}"

    def run_cli_query(self) -> Data:
        """Executes a query to the Claude Code CLI."""
        try:
            # Check CLI availability first
            cli_available, cli_status = self._check_claude_cli()

            if self.debug:
                self.log(f"CLI Status: {cli_status}")

            if not cli_available:
                error_msg = (
                    f"Claude CLI not available: {cli_status}\n\n"
                    "TROUBLESHOOTING:\n"
                    "1. Install Claude Code CLI: pip install claude-code\n"
                    "2. Authenticate: run 'claude' in terminal and login\n"
                    "3. Verify: run 'claude --version'\n"
                    "4. Ensure claude is in your PATH"
                )
                self.status = "CLI not available"
                return Data(data={"error": error_msg, "text": error_msg})

            # Execute the query
            result = self._execute_claude_query(self.prompt)

            # Check if result is an error
            if result.startswith("Error:"):
                self.status = "CLI execution failed"
                return Data(data={"error": result, "text": result})

            self.status = "CLI execution completed successfully"
            return Data(data={"text": result})

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.status = error_msg
            if self.debug:
                self.log(error_msg)
            return Data(data={"error": error_msg, "text": error_msg})
