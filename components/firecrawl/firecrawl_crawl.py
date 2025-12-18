import uuid

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, IntInput, MultilineInput, Output, SecretStrInput, StrInput, TabInput
from lfx.schema.data import Data
from lfx.utils.component_utils import set_current_fields, set_field_display

# Define fields for each instance type
INSTANCE_TYPE_FIELDS = {
    "Cloud": ["api_key"],
    "Self-Hosted": ["base_url"],
}

# Fields that should always be visible
DEFAULT_FIELDS = ["instance_type", "url", "timeout", "idempotency_key", "crawlerOptions", "scrapeOptions"]


class FirecrawlCrawlApi(Component):
    display_name: str = "Firecrawl Crawl API"
    description: str = "Crawls a URL and returns the results."
    name = "FirecrawlCrawlApi"

    documentation: str = "https://docs.firecrawl.dev/v1/api-reference/endpoint/crawl-post"

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
            name="url",
            display_name="URL",
            required=True,
            info="The URL to scrape.",
            tool_mode=True,
        ),
        IntInput(
            name="timeout",
            display_name="Timeout",
            info="Timeout in milliseconds for the request.",
        ),
        StrInput(
            name="idempotency_key",
            display_name="Idempotency Key",
            info="Optional idempotency key to ensure unique requests.",
        ),
        DataInput(
            name="crawlerOptions",
            display_name="Crawler Options",
            info="The crawler options to send with the request.",
        ),
        DataInput(
            name="scrapeOptions",
            display_name="Scrape Options",
            info="The page options to send with the request.",
        ),
    ]

    outputs = [
        Output(display_name="Data", name="data", method="crawl"),
    ]
    idempotency_key: str | None = None

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

    def crawl(self) -> Data:
        try:
            from firecrawl import FirecrawlApp
        except ImportError as e:
            msg = "Could not import firecrawl integration package. Please install it with `pip install firecrawl-py`."
            raise ImportError(msg) from e

        params = self.crawlerOptions.__dict__["data"] if self.crawlerOptions else {}
        scrape_options_dict = self.scrapeOptions.__dict__["data"] if self.scrapeOptions else {}
        if scrape_options_dict:
            params["scrapeOptions"] = scrape_options_dict

        # Set default values for new parameters in v1
        params.setdefault("maxDepth", 2)
        params.setdefault("limit", 10000)
        params.setdefault("allowExternalLinks", False)
        params.setdefault("allowBackwardLinks", False)
        params.setdefault("ignoreSitemap", False)
        params.setdefault("ignoreQueryParameters", False)

        # Ensure onlyMainContent is explicitly set if not provided
        if "scrapeOptions" in params:
            params["scrapeOptions"].setdefault("onlyMainContent", True)
        else:
            params["scrapeOptions"] = {"onlyMainContent": True}

        if not self.idempotency_key:
            self.idempotency_key = str(uuid.uuid4())

        # Initialize FirecrawlApp based on instance type
        app_kwargs = {}
        if self.instance_type == "Self-Hosted":
            if not self.base_url:
                raise ValueError("Base URL is required for self-hosted instances.")
            app_kwargs["api_url"] = self.base_url.rstrip("/")
            # API key is optional for self-hosted instances
            if self.api_key:
                app_kwargs["api_key"] = self.api_key
        else:  # Cloud
            if not self.api_key:
                raise ValueError("API key is required for cloud instances.")
            app_kwargs["api_key"] = self.api_key
        
        app = FirecrawlApp(**app_kwargs)
        crawl_result = app.crawl_url(self.url, params=params, idempotency_key=self.idempotency_key)
        return Data(data={"results": crawl_result})
