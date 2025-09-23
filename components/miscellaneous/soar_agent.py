from lfx.custom.custom_component.component import Component
from lfx.inputs import MessageTextInput, StrInput, FileInput
from lfx.io import Output
from lfx.schema import Data, Message
from lfx.logging import logger

try:
    from pysoarlib import Agent
    SOAR_AVAILABLE = True
except ImportError:
    SOAR_AVAILABLE = False
    Agent = None


class SOARAgentComponent(Component):
    """
    SOAR Agent component for cognitive architecture integration.
    
    This component integrates with SOAR cognitive architecture to provide
    intelligent decision-making capabilities in Langflow flows.
    """
    
    display_name = "SOAR Agent"
    description = "Integration with SOAR cognitive architecture for intelligent decision making"
    name = "SOARAgent"
    icon = "brain"
    
    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="Text input to be processed by the SOAR agent",
            required=True,
        ),
        StrInput(
            name="agent_name",
            display_name="Agent Name",
            info="Name for the SOAR agent instance",
            value="langflow_soar",
            required=True,
        ),
        FileInput(
            name="productions_file",
            display_name="Productions File",
            info="SOAR productions file (.soar) to load",
            required=False,
            file_types=["soar", "txt"],
        ),
        StrInput(
            name="productions_path",
            display_name="Productions Path",
            info="Path to SOAR productions file (alternative to file upload)",
            required=False,
        ),
        StrInput(
            name="run_phases",
            display_name="Run Phases",
            info="Number of decision cycles to run (default: 1)",
            value="1",
            required=False,
        ),
    ]
    
    outputs = [
        Output(
            display_name="SOAR Response",
            name="soar_response",
            method="execute_soar_agent"
        ),
        Output(
            display_name="SOAR Debug Info",
            name="soar_debug",
            method="get_debug_info"
        ),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.soar_agent = None
        self._initialized = False
    
    def _initialize_agent(self):
        """Initialize the SOAR agent if not already done."""
        if self._initialized and self.soar_agent is not None:
            return
            
        if not SOAR_AVAILABLE:
            raise ImportError(
                "SOAR library not available. Please install pysoarlib: "
                "pip install pysoarlib"
            )
        
        try:
            agent_name = getattr(self, 'agent_name', 'langflow_soar')
            self.soar_agent = Agent(agent_name)
            self.log(f"SOAR agent '{agent_name}' initialized successfully")
            
            # Load productions if provided
            self._load_productions()
            
            self._initialized = True
            self.log("SOAR agent initialization completed")
            
        except Exception as e:
            self.log(f"Error initializing SOAR agent: {str(e)}")
            raise ValueError(f"Failed to initialize SOAR agent: {e!s}") from e
    
    def _load_productions(self):
        """Load SOAR productions from file or path."""
        productions_path = None
        
        # Try to get productions from file upload first
        if hasattr(self, 'productions_file') and self.productions_file:
            try:
                resolved_files = self.resolve_path()
                if resolved_files:
                    productions_path = resolved_files[0]
                    self.log(f"Loading productions from uploaded file: {productions_path}")
            except Exception as e:
                self.log(f"Error resolving productions file: {str(e)}")
        
        # Fallback to path input
        if not productions_path and hasattr(self, 'productions_path') and self.productions_path:
            productions_path = self.productions_path
            self.log(f"Loading productions from path: {productions_path}")
        
        if productions_path:
            try:
                self.soar_agent.load_productions(productions_path)
                self.log(f"Productions loaded successfully from: {productions_path}")
            except Exception as e:
                self.log(f"Error loading productions: {str(e)}")
                # Don't raise error - agent can work without productions
        else:
            self.log("No productions file provided - using default agent behavior")
    
    def execute_soar_agent(self) -> Data:
        """Execute the SOAR agent with input text."""
        try:
            # Initialize agent if needed
            self._initialize_agent()
            
            # Get input text
            input_text = getattr(self, 'input_text', '')
            if not input_text:
                return Data(data={
                    "response": "No input text provided",
                    "error": "Input text is required"
                })
            
            # Clear previous output and add input to working memory
            self.soar_agent.clear_output()
            self.soar_agent.add_wme("io", "input", input_text)
            
            # Run decision cycles
            run_phases = int(getattr(self, 'run_phases', 1))
            self.log(f"Running SOAR agent for {run_phases} decision cycles")
            
            self.soar_agent.run_for_n_phases(run_phases)
            
            # Get output from agent
            output = self.soar_agent.get_output_string()
            
            if not output:
                output = "No response generated by SOAR agent"
            
            self.log(f"SOAR agent execution completed. Output: {output}")
            
            return Data(data={
                "response": output,
                "input_text": input_text,
                "run_phases": run_phases,
                "agent_name": getattr(self, 'agent_name', 'langflow_soar')
            })
            
        except Exception as e:
            self.log(f"Error executing SOAR agent: {str(e)}")
            return Data(data={
                "response": f"Error: {str(e)}",
                "error": str(e),
                "input_text": getattr(self, 'input_text', ''),
                "agent_name": getattr(self, 'agent_name', 'langflow_soar')
            })
    
    def get_debug_info(self) -> Data:
        """Get debug information about the SOAR agent state."""
        try:
            self._initialize_agent()
            
            debug_info = {
                "agent_name": getattr(self, 'agent_name', 'langflow_soar'),
                "initialized": self._initialized,
                "agent_available": self.soar_agent is not None,
                "productions_loaded": hasattr(self, 'productions_file') or hasattr(self, 'productions_path'),
                "input_text": getattr(self, 'input_text', ''),
                "run_phases": getattr(self, 'run_phases', '1'),
            }
            
            if self.soar_agent:
                try:
                    # Get working memory elements
                    wme_count = len(self.soar_agent.get_wmes()) if hasattr(self.soar_agent, 'get_wmes') else 0
                    debug_info["working_memory_elements"] = wme_count
                except Exception as e:
                    debug_info["working_memory_error"] = str(e)
            
            self.log(f"Debug info collected: {debug_info}")
            return Data(data=debug_info)
            
        except Exception as e:
            self.log(f"Error getting debug info: {str(e)}")
            return Data(data={
                "error": str(e),
                "agent_available": False,
                "initialized": False
            })
    
    def validate_inputs(self) -> None:
        """Validate component inputs."""
        if not SOAR_AVAILABLE:
            raise ImportError(
                "SOAR library not available. Please install pysoarlib: "
                "pip install pysoarlib"
            )
        
        input_text = getattr(self, 'input_text', '')
        if not input_text:
            raise ValueError("Input text is required")
        
        agent_name = getattr(self, 'agent_name', '')
        if not agent_name:
            raise ValueError("Agent name is required")
        
        # Validate run_phases
        try:
            run_phases = int(getattr(self, 'run_phases', 1))
            if run_phases <= 0:
                raise ValueError("Run phases must be positive")
        except (ValueError, TypeError):
            raise ValueError("Run phases must be a valid positive integer")
