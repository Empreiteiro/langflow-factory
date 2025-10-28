from langflow.custom import Component
from langflow.io import StrInput, Output, DropdownInput, BoolInput
from langflow.schema import Data
import asyncio
import subprocess
import shutil
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


class ClaudeCodeCLIComponent(Component):
    display_name = "Claude Code CLI"
    description = (
        "Executes queries to Claude Code via CLI using claude_agent_sdk.query. "
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
        """Check if Claude CLI is available and working."""
        claude_path = shutil.which("claude")
        if not claude_path:
            return False, "Claude CLI not found in PATH"
        
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, f"Claude CLI failed: {result.stderr}"
            version = result.stdout.strip() or "version unknown"
            return True, f"Claude CLI found at {claude_path}, version: {version}"
        except Exception as e:
            return False, f"Error checking Claude CLI: {e}"

    def run_cli_query(self) -> Data:
        """Executes a query to the Claude Code CLI."""

        async def _run_cli(prompt: str):
            try:
                # Check CLI availability
                cli_available, cli_status = self._check_claude_cli()
                if self.debug:
                    self.log(f"Claude CLI status: {cli_status}")
                
                if not cli_available:
                    return f"Claude CLI not available: {cli_status}"
                
                options = ClaudeAgentOptions(
                    system_prompt=self.system_prompt or "",
                    cwd=self.working_directory or None,
                )

                if self.debug:
                    self.log(f"Executing via CLI with options: {options}")

                output_text = ""

                async for message in query(prompt=prompt, options=options):
                    try:
                        if isinstance(message, AssistantMessage):
                            if hasattr(message, 'content') and message.content:
                                for block in message.content:
                                    if isinstance(block, TextBlock) and hasattr(block, 'text'):
                                        output_text += block.text + "\n"
                                    elif hasattr(block, 'text'):
                                        output_text += str(block.text) + "\n"
                        elif isinstance(message, ResultMessage):
                            # Handle ResultMessage - check common attributes
                            if hasattr(message, 'text'):
                                output_text += f"{message.text}\n"
                            elif hasattr(message, 'status'):
                                output_text += f"[Result: {message.status}]\n"
                            elif hasattr(message, '__dict__'):
                                output_text += f"[Result] {str(message)}\n"
                            else:
                                output_text += f"{str(message)}\n"
                        else:
                            # Handle any other message types
                            output_text += f"{str(message)}\n"
                            
                        if self.debug:
                            self.log(f"Message type: {type(message).__name__}, attributes: {dir(message)}")
                            
                    except Exception as msg_error:
                        if self.debug:
                            self.log(f"Error processing message: {msg_error}")
                        output_text += f"[Message processing error: {str(msg_error)}]\n"

                return output_text.strip() or "No response from Claude."
            except Exception as e:
                error_str = str(e)
                
                # If it's a subprocess/command error, provide more details
                if "Command failed with exit code" in error_str or "exit code" in error_str:
                    cli_available, cli_status = self._check_claude_cli()
                    detailed_error = (
                        f"Failed to execute Claude Code query.\n\n"
                        f"CLI Status: {cli_status}\n\n"
                        f"Error: {error_str}\n\n"
                        "TROUBLESHOOTING:\n"
                        "1. Ensure Claude CLI is installed and authenticated\n"
                        "2. Try running 'claude' in your terminal to start a session\n"
                        "3. Check if you're authenticated: verify with 'claude --version'\n"
                        "4. The claude_agent_sdk may require a running Claude Code session\n"
                    )
                    return detailed_error
                
                if self.debug:
                    self.log(f"Error details: {error_str}")
                
                return f"Error executing Claude Code CLI: {e}"

        try:
            result = asyncio.run(_run_cli(self.prompt))
            self.status = "CLI execution completed successfully."
            return Data(data={"text": result})
        except RuntimeError:
            # Fallback if there's already an active loop
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(_run_cli(self.prompt))
                self.status = "CLI execution completed (existing loop)."
                return Data(data={"text": result})
            except Exception as e:
                msg = f"Error executing with existing loop: {e}"
                self.log(msg)
                return Data(data={"error": msg})
        except Exception as e:
            msg = f"General CLI execution failure: {e}"
            self.status = msg
            self.log(msg)
            return Data(data={"error": msg})
