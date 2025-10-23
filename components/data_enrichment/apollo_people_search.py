from langflow.custom import Component
from langflow.io import StrInput, IntInput, Output, SecretStrInput
from langflow.schema import DataFrame
import requests
import pandas as pd
import json

class ApolloPeopleSearch(Component):
    """
    People search using Apollo's People Search endpoint.

    Inputs (examples):
      - person_first_name: "John"
      - person_last_name: "Doe"
      - person_emails: "john@ex.com,j.doe@ex.com"
      - person_titles: "Director,Head of Sales"
      - person_organization_names: "Google" (single name only)
      - person_organization_domains: "google.com,alphabet.com"
      - person_locations: "San Francisco, CA, United States,US"
      - organization_locations: "San Francisco, US"
      - page: 1
      - per_page: 10 (1-100)
    """

    display_name = "Apollo People Search"
    description = "People Search (Apollo API) — POST /api/v1/mixed_people/search"
    icon = "account-search"
    name = "ApolloPeopleSearch"

    inputs = [
        SecretStrInput(name="api_key", display_name="API Key", required=True, info="Your Apollo API Key."),
        StrInput(name="person_first_name", display_name="First name", advanced=True, tool_mode=True),
        StrInput(name="person_last_name", display_name="Last name", advanced=True, tool_mode=True),
        StrInput(name="person_emails", display_name="Emails (comma-separated)", advanced=True, tool_mode=True),
        StrInput(name="person_titles", display_name="Titles (comma-separated)", advanced=True, tool_mode=True),
        StrInput(name="person_organization_names", display_name="Organization name", advanced=True, tool_mode=True, info="Single organization name to search for."),
        StrInput(name="person_organization_domains", display_name="Organization domains (comma-separated)", advanced=True, tool_mode=True),
        StrInput(name="person_locations", display_name="Person locations (comma-separated)", advanced=True, tool_mode=True),
        StrInput(name="organization_locations", display_name="Organization locations (comma-separated)", advanced=True, tool_mode=True),
        IntInput(name="page", display_name="Page", value=1, info="Page number."),
        IntInput(name="per_page", display_name="Per Page", value=10, info="Results per page (1-100)."),
    ]

    outputs = [
        Output(name="results", display_name="Search Results", method="search_people"),
    ]

    def _to_list(self, value):
        """Converts CSV string to list; if already a list, returns as is; None/'' -> None."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            lst = [v for v in value if v is not None and str(v).strip() != ""]
            return lst if lst else None
        s = str(value).strip()
        if s == "":
            return None
        # split by comma and trim spaces
        items = [p.strip() for p in s.split(",") if p.strip()]
        return items if items else None

    def search_people(self) -> DataFrame:
        url = "https://api.apollo.io/api/v1/mixed_people/search"
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-api-key": self.api_key,
        }

        # build payload (endpoint accepts arrays in JSON body)
        payload = {}
        # pagination (docs: per_page 1-100)
        try:
            payload["page"] = int(self.page) if self.page is not None else 1
        except Exception:
            payload["page"] = 1
        try:
            per_page_val = int(self.per_page) if self.per_page is not None else 10
            payload["per_page"] = max(1, min(100, per_page_val))
        except Exception:
            payload["per_page"] = 10

        # simple scalar fields
        if getattr(self, "person_first_name", None):
            payload["person_first_name"] = self.person_first_name
        if getattr(self, "person_last_name", None):
            payload["person_last_name"] = self.person_last_name
        
        # q_organization_name is a string (not array) - get first value if multiple provided
        if getattr(self, "person_organization_names", None):
            org_names = self._to_list(self.person_organization_names)
            if org_names:
                payload["q_organization_name"] = org_names[0]  # API accepts single string

        # fields that should be arrays
        for src_name, payload_name in [
            ("person_emails", "person_emails"),
            ("person_titles", "person_titles"),
            ("person_organization_domains", "organization_domains"),
            ("person_locations", "person_locations"),
            ("organization_locations", "organization_locations"),
        ]:
            val = self._to_list(getattr(self, src_name, None))
            if val:
                payload[payload_name] = val

        # logs for debugging
        self.log("=== APOLLO PEOPLE SEARCH ===")
        self.log(f"URL: {url}")
        self.log(f"Page: {payload.get('page')}, Per page: {payload.get('per_page')}")
        provided = {k: v for k, v in payload.items() if k not in ("page", "per_page")}
        if provided:
            self.log(f"Filters provided: {', '.join(provided.keys())}")
        else:
            self.log("No specific filters provided (broad search — consumes credits).")

        try:
            # show payload for debug (be careful with logs in production)
            try:
                self.log("Payload JSON:")
                self.log(json.dumps(payload, ensure_ascii=False, indent=2))
            except Exception:
                pass

            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self.log(f"Status: {resp.status_code}")

            # response has 'people' according to docs
            people = data.get("people") if isinstance(data, dict) else None
            if not people:
                # some endpoints/integrations may return 'results' or 'contacts'
                if isinstance(data, dict) and data.get("contacts"):
                    people = data.get("contacts")
                elif isinstance(data, dict) and data.get("results"):
                    people = data.get("results")

            if not people:
                self.log("No people found in response.")
                # return raw response for debugging
                try:
                    return DataFrame(pd.DataFrame({"message": ["No people found."], "raw_response": [json.dumps(data, ensure_ascii=False)]}))
                except Exception:
                    return DataFrame(pd.DataFrame({"message": ["No people found."]}))

            # convert to DataFrame
            df = pd.DataFrame(people)
            self.log(f"Found {len(df)} people — returning DataFrame.")
            return DataFrame(df)

        except requests.exceptions.RequestException as e:
            err = f"Request error: {e}"
            self.log(err)
            self.status = err
            return DataFrame(pd.DataFrame({"error": [str(e)]}))

        except Exception as e:
            err = f"Unexpected error: {e}"
            self.log(err)
            self.status = err
            return DataFrame(pd.DataFrame({"error": [str(e)]}))
