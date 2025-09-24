import random
from langflow.custom import Component
from langflow.io import BoolInput, Output, HandleInput, TableInput
from langflow.schema.message import Message
from langflow.schema.data import Data
from typing import Any


class RandomRouterComponent(Component):
    display_name = "Random Router"
    description = "Routes input data to random paths based on configurable probabilities."
    icon = "shuffle"
    name = "RandomRouter"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_route = None

    inputs = [
        HandleInput(
            name="input_data",
            display_name="Input Data",
            info="Any type of input data to route.",
            input_types=["Text", "Data", "DataFrame", "Message"],
            required=True,
        ),
        TableInput(
            name="routes",
            display_name="Routes",
            info="Define the routes for random routing. Set the percentage chance for each route (must total 100%). Use Custom Output to override the input data for specific routes.",
            table_schema=[
                {"name": "route_name", "display_name": "Route Name", "type": "str", "description": "Name for the route (used as output name)"},
                {"name": "percentage", "display_name": "Percentage (%)", "type": "float", "description": "Chance of selecting this route (0-100)"},
                {"name": "output_value", "display_name": "Custom Output", "type": "str", "description": "Custom output value for this route. Leave blank to use the input data as output.", "default": ""},
            ],
            value=[
                {"route_name": "Route A", "percentage": 50.0, "output_value": ""},
                {"route_name": "Route B", "percentage": 50.0, "output_value": ""}
            ],
            real_time_refresh=True,
            required=True,
        ),
        BoolInput(
            name="enable_else_output",
            display_name="Include Else Output",
            info="Include an Else output for cases that don't match any route (when percentages don't total 100%).",
            value=False,
            advanced=True,
        ),
    ]

    outputs = []

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Create a dynamic output for each route in the routes table."""
        if field_name == "routes" or field_name == "enable_else_output":
            frontend_node["outputs"] = []
            
            # Get the routes data - either from field_value (if routes field) or from component state
            if field_name == "routes":
                routes_data = field_value
            else:
                routes_data = getattr(self, "routes", [])
            
            # Add a dynamic output for each route - all using the same method
            for i, row in enumerate(routes_data):
                route_name = row.get("route_name", f"Route {i+1}")
                percentage = row.get("percentage", 0.0)
                
                frontend_node["outputs"].append(
                    Output(
                        display_name=f"{route_name} ({percentage}%)",
                        name=f"route_{i+1}_result",
                        method="process_route",
                        group_outputs="True"
                    )
                )
            # Add default output only if enabled
            if field_name == "enable_else_output":
                enable_else = field_value
            else:
                enable_else = getattr(self, "enable_else_output", False)
            
            if enable_else:
                frontend_node["outputs"].append(
                    Output(display_name="Else", name="default_result", method="default_response", group_outputs=True)
                )
        return frontend_node

    def _perform_selection(self):
        """Perform the random selection once and store the result."""
        routes = getattr(self, "routes", [])
        
        if not routes:
            self._selected_route = -1
            return
        
        # Validate percentages and calculate total
        total_percentage = 0
        valid_routes = []
        
        for i, route in enumerate(routes):
            percentage = route.get("percentage", 0.0)
            try:
                percentage = float(percentage)
                if percentage < 0:
                    percentage = 0
                elif percentage > 100:
                    percentage = 100
                total_percentage += percentage
                valid_routes.append((i, percentage, route))
            except (ValueError, TypeError):
                continue
        
        if not valid_routes:
            self._selected_route = -1
            return
        
        # Normalize percentages if they don't total 100%
        if total_percentage != 100.0:
            if total_percentage == 0:
                # Distribute equally
                equal_percentage = 100.0 / len(valid_routes)
                valid_routes = [(i, equal_percentage, route) for i, _, route in valid_routes]
            else:
                # Normalize to 100%
                valid_routes = [(i, (percentage / total_percentage) * 100, route) for i, percentage, route in valid_routes]
        
        # Generate random number (0-100)
        random_value = random.uniform(0, 100)
        
        # Find selected route based on cumulative percentage
        cumulative_percentage = 0
        selected_route_index = None
        
        for i, percentage, route in valid_routes:
            cumulative_percentage += percentage
            if random_value <= cumulative_percentage:
                selected_route_index = i
                break
                
        if selected_route_index is None:
            # Fallback to last route
            selected_route_index = valid_routes[-1][0]
        
        self._selected_route = selected_route_index
        
        # Log the selection
        route_name = routes[selected_route_index].get("route_name", f"Route {selected_route_index+1}")
        self.log(f"Random selection: {route_name} (route index: {selected_route_index}, random value: {random_value:.2f})")
        self.status = f"Selected: {route_name} ({selected_route_index})"

    def process_route(self) -> Message:
        """Process all routes using random selection and return message for selected route."""
        # Only perform selection if not already done
        if not hasattr(self, '_selected_route') or self._selected_route is None:
            routes = getattr(self, "routes", [])
            input_data = getattr(self, "input_data", None)
            
            if not routes:
                self.status = "No routes configured"
                return Message(text="No routes configured")
            
            # Perform random selection
            self._perform_selection()
        
        routes = getattr(self, "routes", [])
        input_data = getattr(self, "input_data", None)
        
        if hasattr(self, '_selected_route') and self._selected_route is not None and self._selected_route != -1:
            # A route was selected
            selected_route_index = self._selected_route
            
            # Stop all route outputs except the selected one
            for i in range(len(routes)):
                if i != selected_route_index:
                    self.stop(f"route_{i+1}_result")
            
            # Also stop the default output (if it exists)
            enable_else = getattr(self, "enable_else_output", False)
            if enable_else:
                self.stop("default_result")
            
            route_name = routes[selected_route_index].get("route_name", f"Route {selected_route_index+1}")
            self.status = f"Randomly selected: {route_name}"
            
            # Check if there's a custom output value for this route
            custom_output = routes[selected_route_index].get("output_value", "")
            if custom_output and str(custom_output).strip() and str(custom_output).strip().lower() != "none":
                # Use custom output value
                return Message(text=str(custom_output))
            else:
                # Use input data as default output - extract only text content
                if hasattr(input_data, 'text'):
                    return Message(text=str(input_data.text) if input_data.text else "")
                else:
                    return Message(text=str(input_data) if input_data else "")
        else:
            # No route was selected (should not happen with proper percentages)
            # Stop all route outputs
            for i in range(len(routes)):
                self.stop(f"route_{i+1}_result")
            
            # Check if else output is enabled
            enable_else = getattr(self, "enable_else_output", False)
            if enable_else:
                # The default_response will handle the else case
                self.stop("process_route")
                return Message(text="")
            else:
                # No else output, so no output at all
                self.status = "No route selected and Else output is disabled"
                return Message(text="")

    def default_response(self) -> Message:
        """Handle the else case when no route is selected."""
        # Check if else output is enabled
        enable_else = getattr(self, "enable_else_output", False)
        if not enable_else:
            self.status = "Else output is disabled"
            return Message(text="")
        
        # Clear any previous match state if not already set
        if not hasattr(self, '_selected_route'):
            self._selected_route = None
            
        routes = getattr(self, "routes", [])
        input_data = getattr(self, "input_data", None)
        
        # Check if a route was already selected in process_route
        if hasattr(self, '_selected_route') and self._selected_route is not None:
            self.status = f"Route {self._selected_route + 1} was already selected, stopping default_response"
            self.stop("default_result")
            return Message(text="")
        
        # No route was selected (fallback case)
        self.status = "No route selected - using input data as fallback for Else output"
        if hasattr(input_data, 'text'):
            return Message(text=str(input_data.text) if input_data.text else "")
        else:
            return Message(text=str(input_data) if input_data else "")
