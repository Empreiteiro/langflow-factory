from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, MultilineInput, Output, SecretStrInput, StrInput, TabInput
from lfx.logging.logger import logger
from lfx.schema.data import Data
from lfx.utils.component_utils import set_current_fields, set_field_display

# Define fields for each instance type
INSTANCE_TYPE_FIELDS = {
    "Cloud": ["api_key"],
    "Self-Hosted": ["base_url"],
}

# Fields that should always be visible
DEFAULT_FIELDS = ["instance_type", "urls", "prompt", "schema", "enable_web_search"]


class FirecrawlExtractApi(Component):
    display_name: str = "Firecrawl Extract API"
    description: str = "Extracts data from a URL."
    name = "FirecrawlExtractApi"

    documentation: str = "https://docs.firecrawl.dev/api-reference/endpoint/extract"

    inputs = [
        TabInput(
            name="instance_type",
            display_name="Instance Type",
            options=["Cloud", "Self-Hosted"],
            value="Cloud",
            real_time_refresh=True,
            info="Select whether to use Firecrawl cloud API or a self-hosted instance.",
        ),
        SecretStrInput(
            name="api_key",
            display_name="Firecrawl API Key",
            required=True,
            password=True,
            show=False,
            info="The API key to use Firecrawl API. Required for cloud instances, optional for self-hosted.",
        ),
        StrInput(
            name="base_url",
            display_name="Base URL",
            required=False,
            show=False,
            info="Base URL for self-hosted Firecrawl instance (e.g., http://localhost:3002). Only used when instance type is 'Self-Hosted'.",
        ),
        MultilineInput(
            name="urls",
            display_name="URLs",
            required=True,
            info="List of URLs to extract data from (separated by commas or new lines).",
            tool_mode=True,
        ),
        MultilineInput(
            name="prompt",
            display_name="Prompt",
            required=True,
            info="Prompt to guide the extraction process.",
            tool_mode=True,
        ),
        DataInput(
            name="schema",
            display_name="Schema",
            required=False,
            info="Schema to define the structure of the extracted data.",
        ),
        BoolInput(
            name="enable_web_search",
            display_name="Enable Web Search",
            info="When true, the extraction will use web search to find additional data.",
        ),
        # # Optional: Not essential for basic extraction
        # BoolInput(
        #     name="ignore_sitemap",
        #     display_name="Ignore Sitemap",
        #     info="When true, sitemap.xml files will be ignored during website scanning.",
        # ),
        # # Optional: Not essential for basic extraction
        # BoolInput(
        #     name="include_subdomains",
        #     display_name="Include Subdomains",
        #     info="When true, subdomains of the provided URLs will also be scanned.",
        # ),
        # # Optional: Not essential for basic extraction
        # BoolInput(
        #     name="show_sources",
        #     display_name="Show Sources",
        #     info="When true, the sources used to extract the data will be included in the response.",
        # ),
    ]

    outputs = [
        Output(display_name="Data", name="data", method="extract"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update build configuration to show/hide fields based on instance type."""
        if field_name != "instance_type" and field_name is not None:
            return build_config
        
        # Get current instance type
        if field_name == "instance_type":
            instance_type = field_value if isinstance(field_value, str) else "Cloud"
        else:
            # On initial load, get from build_config
            if isinstance(build_config, dict):
                instance_type = build_config.get("instance_type", {}).get("value", "Cloud")
            else:
                instance_type = getattr(build_config.instance_type, "value", "Cloud") if hasattr(build_config, "instance_type") else "Cloud"
        
        # Update field visibility using set_current_fields
        return set_current_fields(
            build_config=build_config,
            action_fields=INSTANCE_TYPE_FIELDS,
            selected_action=instance_type,
            default_fields=DEFAULT_FIELDS,
            func=set_field_display,
            default_value=False,
        )

    def extract(self) -> Data:
        try:
            from firecrawl import FirecrawlApp
        except ImportError as e:
            msg = "Could not import firecrawl integration package. Please install it with `pip install firecrawl-py`."
            raise ImportError(msg) from e

        # Validate API key for cloud instances
        if self.instance_type == "Cloud" and not self.api_key:
            msg = "API key is required for cloud instances"
            raise ValueError(msg)
        
        # Validate base_url for self-hosted instances
        if self.instance_type == "Self-Hosted" and not self.base_url:
            msg = "Base URL is required for self-hosted instances"
            raise ValueError(msg)

        # Validate URLs
        if not self.urls:
            msg = "URLs are required"
            raise ValueError(msg)

        # Split and validate URLs (handle both commas and newlines)
        urls = [url.strip() for url in self.urls.replace("\n", ",").split(",") if url.strip()]
        if not urls:
            msg = "No valid URLs provided"
            raise ValueError(msg)

        # Validate and process prompt
        if not self.prompt:
            msg = "Prompt is required"
            raise ValueError(msg)

        # Get the prompt text (handling both string and multiline input)
        prompt_text = self.prompt.strip()

        # Enhance the prompt to encourage comprehensive extraction
        enhanced_prompt = prompt_text
        if "schema" not in prompt_text.lower():
            enhanced_prompt = f"{prompt_text}. Please extract all instances in a comprehensive, structured format."

        params = {
            "prompt": enhanced_prompt,
            "enableWebSearch": self.enable_web_search,
            # Optional parameters - not essential for basic extraction
            "ignoreSitemap": getattr(self, "ignore_sitemap", False),
            "includeSubdomains": getattr(self, "include_subdomains", False),
            "showSources": getattr(self, "show_sources", False),
            "timeout": 300,
        }

        # Only add schema to params if it's provided and is a valid schema structure
        if self.schema:
            try:
                if isinstance(self.schema, dict) and "type" in self.schema:
                    params["schema"] = self.schema
                elif hasattr(self.schema, "dict") and "type" in self.schema.dict():
                    params["schema"] = self.schema.dict()
                else:
                    # Skip invalid schema without raising an error
                    pass
            except Exception as e:  # noqa: BLE001
                logger.error(f"Invalid schema: {e!s}")

        try:
            # Initialize FirecrawlApp based on instance type
            app_kwargs = {}
            if self.instance_type == "Self-Hosted":
                app_kwargs["api_url"] = self.base_url.rstrip("/")
                # API key is optional for self-hosted instances
                if self.api_key:
                    app_kwargs["api_key"] = self.api_key
            else:  # Cloud
                app_kwargs["api_key"] = self.api_key
            
            app = FirecrawlApp(**app_kwargs)
            extract_result = app.extract(urls, params=params)
            return Data(data=extract_result)
        except Exception as e:
            msg = f"Error during extraction: {e!s}"
            raise ValueError(msg) from e
