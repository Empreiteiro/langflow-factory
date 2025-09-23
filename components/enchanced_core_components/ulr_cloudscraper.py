import re
import cloudscraper
from bs4 import BeautifulSoup
from langchain_community.document_loaders import RecursiveUrlLoader
from loguru import logger

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.helpers.data import safe_convert
from lfx.io import (
    BoolInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    SliderInput,
    TableInput,
)
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from lfx.services.deps import get_settings_service

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_DEPTH = 1
DEFAULT_FORMAT = "Text"

URL_REGEX = re.compile(
    r"^(https?:\/\/)?" r"(www\.)?" r"([a-zA-Z0-9.-]+)" r"(\.[a-zA-Z]{2,})?" r"(:\d+)?" r"(\/[^\s]*)?$",
    re.IGNORECASE,
)


class URLComponent(Component):
    display_name = "URL"
    description = "Fetch content from one or more web pages, including those protected by Cloudflare."
    documentation = "https://docs.langflow.org/components-data#url"
    icon = "layout-template"
    name = "URLComponent"

    inputs = [
        MessageTextInput(
            name="urls",
            display_name="URLs",
            info="Enter one or more URLs to crawl recursively.",
            is_list=True,
            tool_mode=True,
            placeholder="Enter a URL...",
            list_add_label="Add URL",
        ),
        SliderInput(
            name="max_depth",
            display_name="Depth",
            info="Controls how many links deep the crawler will go.",
            value=DEFAULT_MAX_DEPTH,
            range_spec=RangeSpec(min=1, max=5, step=1),
        ),
        BoolInput(
            name="prevent_outside",
            display_name="Prevent Outside",
            info="Only crawl within the root domain.",
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="use_async",
            display_name="Use Async",
            info="Use asynchronous loading.",
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="format",
            display_name="Output Format",
            info="Choose to extract clean text or raw HTML.",
            options=["Text", "HTML"],
            value=DEFAULT_FORMAT,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name="Timeout",
            info="Timeout for each request.",
            value=DEFAULT_TIMEOUT,
            advanced=True,
        ),
        TableInput(
            name="headers",
            display_name="Headers",
            info="Headers to include in the request.",
            table_schema=[
                {"name": "key", "display_name": "Header", "type": "str"},
                {"name": "value", "display_name": "Value", "type": "str"},
            ],
            value=[{"key": "User-Agent", "value": get_settings_service().settings.user_agent}],
            advanced=True,
        ),
        BoolInput(name="filter_text_html", display_name="Filter Text/HTML", value=True, advanced=True),
        BoolInput(name="continue_on_failure", display_name="Continue on Failure", value=True, advanced=True),
        BoolInput(name="check_response_status", display_name="Check Response Status", value=False, advanced=True),
        BoolInput(name="autoset_encoding", display_name="Autoset Encoding", value=True, advanced=True),
    ]

    outputs = [
        Output(display_name="Extracted Pages", name="page_results", method="fetch_content"),
        Output(display_name="Raw Content", name="raw_results", method="fetch_content_as_message"),
    ]

    @staticmethod
    def validate_url(url: str) -> bool:
        return bool(URL_REGEX.match(url))

    def ensure_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        if not self.validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        return url

    def cloudflare_request(self, url: str, headers: dict, timeout: int) -> str:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text

    def fetch_url_contents(self) -> list[dict]:
        urls = list({self.ensure_url(url) for url in self.urls if url.strip()})
        if not urls:
            raise ValueError("No valid URLs provided.")

        headers_dict = {header["key"]: header["value"] for header in self.headers}
        extractor = (lambda x: x) if self.format == "HTML" else (lambda x: BeautifulSoup(x, "lxml").get_text())

        all_docs = []
        for url in urls:
            try:
                raw_html = self.cloudflare_request(url, headers_dict, self.timeout)
                extracted = extractor(raw_html)
                all_docs.append({
                    "text": safe_convert(extracted, clean_data=True),
                    "url": url,
                    "title": "",
                    "description": "",
                    "content_type": "text/html",
                    "language": "",
                })
            except Exception as e:
                self.log(f"Failed to fetch {url}: {e}")
                if not self.continue_on_failure:
                    raise
        if not all_docs:
            raise ValueError("No documents were successfully loaded from any URL")
        return all_docs

    def fetch_content(self) -> DataFrame:
        return DataFrame(data=self.fetch_url_contents())

    def fetch_content_as_message(self) -> Message:
        url_contents = self.fetch_url_contents()
        return Message(text="\n\n".join([x["text"] for x in url_contents]), data={"data": url_contents})
