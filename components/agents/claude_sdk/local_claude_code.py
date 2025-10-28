from langflow.custom import Component
from langflow.io import StrInput, Output, DropdownInput, BoolInput
from langflow.schema import Data
import asyncio
import subprocess
import shutil
from claude_agent_sdk._internal.client import InternalClient
from claude_agent_sdk.types import ClaudeAgentOptions


class ClaudeCodeAgentLocal(Component):
    display_name = "Claude Code Agent"
    description = (
        "Interacts with a local Claude Code instance using the claude_agent_sdk. "
        "IMPORTANT: This requires a running Claude Code development instance, not just the CLI. "
        "The SDK expects an active Claude Code session to be running. "
        "Make sure you have the Claude Code development environment running."
    )
    icon = "bot"
    name = "ClaudeCodeAgentLocal"
    beta = True

    inputs = [
        StrInput(
            name="prompt",
            display_name="Prompt",
            info="Text to be sent to Claude Code.",
            required=True,  
        ),
        StrInput(
            name="system_prompt",
            display_name="System Prompt",
            info="Defines the agent's base behavior.",
            required=False,
        ),
        StrInput(
            name="working_directory",
            display_name="Working Directory",
            info="Sets the execution directory.",
            required=False,
        ),
        DropdownInput(
            name="permission_mode",
            display_name="Permission Mode",
            info="Defines Claude Code tool permissions.",
            options=[
                "default",
                "acceptEdits",
                "bypassPermissions",
            ],
            value="default",
        ),
        BoolInput(
            name="reuse_instance",
            display_name="Reuse Instance",
            info="Reuses the local client between calls.",
            value=True,
        ),
        BoolInput(
            name="debug",
            display_name="Debug",
            info="Enables detailed logs.",
            value=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Claude Response", method="run_agent"),
    ]

    field_order = [
        "prompt",
        "system_prompt",
        "working_directory",
        "permission_mode",
        "reuse_instance",
        "debug",
    ]

    def _check_claude_cli(self):
        """Check if Claude CLI is available."""
        claude_path = shutil.which("claude")
        if not claude_path:
            return False, "Claude CLI not found in PATH"
        
        try:
            # Try to run claude --version to verify it works
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, f"Claude CLI exists but failed: {result.stderr}"
            return True, f"Claude CLI found: {claude_path}"
        except FileNotFoundError:
            return False, "Claude CLI command not found"
        except subprocess.TimeoutExpired:
            return False, "Claude CLI command timed out"
        except Exception as e:
            return False, f"Error checking Claude CLI: {e}"

    def _get_or_create_client(self):
        """Gets a persistent instance of InternalClient."""
        # Check if Claude CLI is available
        cli_available, cli_message = self._check_claude_cli()
        if self.debug:
            self.log(f"Claude CLI check: {cli_message}")
        
        if not cli_available:
            self.log(f"Warning: {cli_message}")
        
        key = f"{self._id}_client"
        client = self.ctx.get(key)
        if not client or not self.reuse_instance:
            client = InternalClient()
            self.update_ctx({key: client})
            if self.debug:
                self.log("New local Claude Code instance created.")
        elif self.debug:
            self.log("Reusing existing local instance.")
        return client

    def run_agent(self) -> Data:
        """Executes the prompt on the local Claude Code instance."""

        async def _run(prompt: str):
            try:
                client = self._get_or_create_client()
                options = ClaudeAgentOptions(
                    system_prompt=self.system_prompt or "",
                    cwd=self.working_directory or None,
                    permission_mode=self.permission_mode or "default",
                )

                if self.debug:
                    self.log(f"Executing local query: {prompt[:100]}...")
                    self.log(f"Options: {options}")

                # Try to verify Claude Code session is accessible
                try:
                    test_result = subprocess.run(
                        ["claude", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if self.debug:
                        self.log(f"Claude CLI version check: {test_result.returncode}, stdout: {test_result.stdout[:100]}")
                except Exception as e:
                    if self.debug:
                        self.log(f"Could not check CLI version: {e}")

                result_text = ""
                async for message in client.process_query(prompt=prompt, options=options):
                    result_text += str(message)

                return result_text
            except Exception as e:
                error_str = str(e)
                
                # Try to get the actual stderr output if it's a subprocess error
                if "Command failed with exit code" in error_str or "exit code" in error_str:
                    # Try to run claude directly to see what the actual error is
                    try:
                        test_result = subprocess.run(
                            ["claude", "--help"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        cli_test_info = f"CLI test: returncode={test_result.returncode}, stdout={test_result.stdout[:100]}, stderr={test_result.stderr[:100]}"
                        if self.debug:
                            self.log(cli_test_info)
                    except Exception as test_e:
                        cli_test_info = f"CLI test failed: {test_e}"
                    
                    # Check if there's a running Claude Code instance
                    cli_available, cli_status = self._check_claude_cli()
                    
                    # Try to get Claude Code version for debugging
                    version_info = "Unknown"
                    try:
                        version_result = subprocess.run(
                            ["claude", "--version"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        version_info = version_result.stdout.strip() if version_result.returncode == 0 else f"Failed with code {version_result.returncode}"
                    except:
                        pass
                    
                    detailed_msg = (
                        f"Failed to connect to Claude Code SDK.\n\n"
                        f"CLI Status: {cli_status}\n"
                        f"CLI Version: {version_info}\n"
                        f"{cli_test_info}\n\n"
                        "TROUBLESHOOTING STEPS:\n"
                        "1. Make sure Claude Code is authenticated: run 'claude' in your terminal\n"
                        "2. Start a Claude Code session in terminal: 'claude'\n"
                        "3. Check SDK compatibility: ensure claude_agent_sdk version matches your CLI\n"
                        "4. Try restarting authentication: 'claude auth' or '/login'\n\n"
                        f"Original error: {error_str}\n\n"
                        "Note: The claude_agent_sdk may need an active Claude Code session running."
                    )
                    return detailed_msg
                return f"Error interacting with local Claude Code instance: {e}"

        try:
            result = asyncio.run(_run(self.prompt))
            self.status = "Local execution completed successfully."
            return Data(data={"text": result})
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(_run(self.prompt))
                self.status = "Local execution completed successfully (existing loop)."
                return Data(data={"text": result})
            except Exception as e:
                msg = f"Error with existing loop: {e}"
                self.log(msg)
                return Data(data={"error": msg})
        except Exception as e:
            error_str = str(e)
            if "Command failed with exit code" in error_str:
                cli_available, cli_status = self._check_claude_cli()
                msg = (
                    f"Claude Code CLI connection failed.\n"
                    f"CLI Status: {cli_status}\n\n"
                    "Troubleshooting:\n"
                    "1. Install CLI: npm install -g @anthropic-ai/claude\n"
                    "2. Authenticate: claude auth\n"
                    "3. Verify: claude --version\n"
                    f"\nError: {error_str}"
                )
            else:
                msg = f"Failed to query local Claude Code instance: {e}"
            
            self.status = msg
            self.log(msg)
            return Data(data={"error": msg})
