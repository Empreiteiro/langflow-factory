from langflow.custom import Component
from langflow.io import StrInput, Output, SecretStrInput
from langflow.schema import Data
import subprocess
import os
import tempfile
import platform


class ClaudeSDKTerminalComponent(Component):
    """
    Claude Agent SDK Terminal Component
    
    This component executes Claude Agent SDK queries in a separate terminal process to avoid 
    conflicts with Langflow. It creates a temporary Python script with the SDK code and runs 
    it in a new terminal.
    
    PREREQUISITES FOR THIS COMPONENT TO WORK:
    
    1. INSTALL CLAUDE AGENT SDK (Python package):
       pip install claude-agent-sdk
       
    2. INSTALL CLAUDE CODE (npm package):
       npm install -g @anthropic-ai/claude-agent-sdk
       
    3. VERIFY INSTALLATIONS:
       - Python SDK: python -c "import claude_agent_sdk; print('SDK installed')"
       - CLI: claude --version
       
    4. AUTHENTICATE:
       - Set ANTHROPIC_API_KEY environment variable, OR
       - Use claude auth login command
       
    5. TEST MANUALLY:
       - CLI: claude -p "Hello world"
       - SDK: python -c "import anyio; from claude_agent_sdk import query; anyio.run(lambda: [print(msg) async for msg in query(prompt='test')])"
    
    HOW THIS COMPONENT WORKS:
    1. Creates a temporary Python script with claude_agent_sdk code
    2. Executes the script in a new terminal process
    3. Captures the output and returns Claude's response
    4. Cleans up temporary files automatically
    
    This approach avoids terminal conflicts with Langflow by running the SDK in isolation.
    """
    display_name = "Claude SDK Terminal"
    description = (
        "Execute prompts using Claude Agent SDK."
    )
    icon = "bot"
    name = "ClaudeSDKTerminalComponent"
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
        Output(name="response", display_name="Claude Response", method="run_sdk_query"),
    ]

    field_order = [
        "api_key",
        "prompt",
    ]

    def _execute_in_new_terminal(self, command_args, env_vars=None):
        """
        Execute a command in a new terminal and return the result.
        
        This method runs commands in a separate process to avoid conflicts with Langflow's terminal.
        It uses subprocess.run with direct argument lists to prevent shell escaping issues.
        
        Args:
            command_args: List of command arguments (e.g., ["python", "script.py"])
            env_vars: Dictionary of environment variables to set
            
        Returns:
            subprocess.CompletedProcess result or None if timeout/error
        """
        try:
            # Prepare environment variables
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Execute command directly with arguments
            result = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutos de timeout
                env=env
            )
            
            return result
            
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

    def run_sdk_query(self) -> Data:
        """
        Execute the prompt using Claude Agent SDK in a new terminal.
        
        This method creates a temporary Python script that imports claude_agent_sdk and uses
        the query() function with anyio for async execution. The script is run in a separate
        terminal process to avoid conflicts with Langflow.
        
        The script structure:
        1. Sets ANTHROPIC_API_KEY environment variable
        2. Uses claude_agent_sdk.query() with the provided prompt
        3. Collects all response messages
        4. Prints "SUCCESS:" or "ERROR:" for result parsing
        
        Returns:
            Data object with Claude's response or error message
        """
        
        try:
            # Create temporary Python script with SDK code
            # This script will be executed in a separate terminal to avoid Langflow conflicts
            script_content = f'''
import anyio
from claude_agent_sdk import query
import os

async def main():
    try:
        # Configure API key for authentication
        os.environ["ANTHROPIC_API_KEY"] = "{self.api_key}"
        
        # Execute query using claude_agent_sdk.query() function
        response_text = ""
        async for message in query(prompt="{self.prompt}"):
            response_text += str(message) + "\\n"
        
        # Print success marker for result parsing
        print("SUCCESS:", response_text.strip())
        
    except Exception as e:
        # Print error marker for error handling
        print("ERROR:", str(e))

# Run the async function using anyio
anyio.run(main)
'''
            
            # Create temporary file to store the Python script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_script = temp_file.name
            
            try:
                # Execute script in new terminal using argument list
                # Using ["python", script_path] avoids shell escaping issues
                command_args = ["python", temp_script]
                env_vars = {"ANTHROPIC_API_KEY": self.api_key}
                result = self._execute_in_new_terminal(command_args, env_vars)
                
                if result is None:
                    error_msg = "SDK query timed out or failed to execute in new terminal"
                    self.status = error_msg
                    return Data(data={"error": error_msg})
                
                if result.returncode == 0:
                    # Parse script output - look for SUCCESS: or ERROR: markers
                    output = result.stdout.strip()
                    
                    if output.startswith("SUCCESS:"):
                        # Success - extract Claude's response after SUCCESS: marker
                        response_text = output.replace("SUCCESS:", "").strip()
                        self.status = "SDK query executed successfully in new terminal."
                        return Data(data={"text": response_text})
                    elif output.startswith("ERROR:"):
                        # SDK error - extract error message after ERROR: marker
                        error_text = output.replace("ERROR:", "").strip()
                        error_msg = f"SDK error in new terminal: {error_text}"
                        self.status = error_msg
                        return Data(data={"error": error_msg})
                    else:
                        # Unexpected output format - return as-is
                        self.status = "SDK query executed successfully in new terminal."
                        return Data(data={"text": output})
                else:
                    # Script execution failed - handle common errors
                    error_msg = f"Script execution error in new terminal: {result.stderr}"
                    
                    # Provide specific solutions for common installation/authentication issues
                    if "ModuleNotFoundError" in result.stderr:
                        error_msg = (
                            "Claude Agent SDK not found in new terminal.\n\n"
                            "SOLUTION:\n"
                            "1. Install: pip install claude-agent-sdk\n"
                            "2. Verify: python -c 'import claude_agent_sdk'\n"
                            "3. Make sure SDK is installed in the same environment as Langflow\n\n"
                            f"Error: {result.stderr}"
                        )
                    elif "not authenticated" in result.stderr.lower():
                        error_msg = (
                            "Authentication failed in new terminal.\n\n"
                            "SOLUTION:\n"
                            "1. Verify your API key is correct\n"
                            "2. Check API key permissions\n"
                            "3. Get a new API key from https://console.anthropic.com/\n\n"
                            f"Error: {result.stderr}"
                        )
                    
                    self.status = error_msg
                    return Data(data={"error": error_msg})
                    
            finally:
                # Clean up temporary file to avoid disk space issues
                try:
                    os.unlink(temp_script)
                except:
                    pass
                
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.status = error_msg
            return Data(data={"error": error_msg})
