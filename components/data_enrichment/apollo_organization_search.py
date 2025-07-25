from langflow.custom import Component
from langflow.io import StrInput, IntInput, BoolInput, Output, SecretStrInput
from langflow.schema import DataFrame, Data
import requests
import pandas as pd
import json

class ApolloOrganizationSearch(Component):
    """
    Orientações de uso dos parâmetros:

    - q_organization_name: str
        Nome da organização (ex: "Google")

    - q_organization_domains: str
        Domínios separados por vírgula (ex: "google.com,alphabet.com")

    - q_organization_locations: str
        Localizações separadas por vírgula (ex: "San Francisco,New York")

    - q_organization_industries: str
        Indústrias separadas por vírgula (ex: "Technology,Finance")

    - q_organization_employee_count_ranges: str
        Faixas de funcionários separadas por vírgula (ex: "1-10,11-50,51-200")

    - q_organization_revenue_ranges: str
        Faixas de receita separadas por vírgula (ex: "0-1M,1M-10M,10M-100M")

    - q_organization_funding_stages: str
        Estágios de investimento separados por vírgula (ex: "Seed,Series A,Series B")

    - q_organization_technologies: str
        Tecnologias separadas por vírgula (ex: "Python,React,Node.js")

    - page: int
        Número da página (ex: 1)

    - per_page: int
        Resultados por página (ex: 10)

    - enrich_domain: bool
        Enriquecer informações de domínio (ex: True ou False)
    """
    display_name = "Apollo Search"
    description = "Search for organizations using the Apollo API."
    icon = "search"
    name = "ApolloOrganizationSearch"

    inputs = [
        SecretStrInput(name="api_key", display_name="API Key", required=True, info="Your Apollo API Key."),
        StrInput(name="q_organization_name", display_name="Organization Name", info="Search by organization name.", advanced=True, tool_mode=True),
        StrInput(name="q_organization_domains", display_name="Organization Domains", info="Search by organization domains (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_locations", display_name="Organization Locations", info="Search by organization locations (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_industries", display_name="Organization Industries", info="Search by organization industries (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_employee_count_ranges", display_name="Employee Count Ranges", info="Search by employee count ranges (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_revenue_ranges", display_name="Revenue Ranges", info="Search by revenue ranges (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_funding_stages", display_name="Funding Stages", info="Search by funding stages (comma-separated).", advanced=True, tool_mode=True),
        StrInput(name="q_organization_technologies", display_name="Technologies", info="Search by technologies used (comma-separated).", advanced=True, tool_mode=True),
        IntInput(name="page", display_name="Page", value=1, info="Page number for pagination.", ),
        IntInput(name="per_page", display_name="Per Page", value=10, info="Number of results per page."),
        BoolInput(name="enrich_domain", display_name="Enrich Domain", value=False, info="Whether to enrich domain info.", advanced=True, tool_mode=True),
    ]

    outputs = [
        Output(name="results", display_name="Search Results", method="search_organizations"),
    ]

    def search_organizations(self) -> DataFrame:
        url = "https://api.apollo.io/v1/organizations/search"
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

        # Build payload from individual inputs
        payload = {
            "page": self.page,
            "per_page": self.per_page,
            "enrich_domain": self.enrich_domain,
        }

        # Add non-empty search parameters
        search_params = []
        if self.q_organization_name:
            payload["q_organization_name"] = self.q_organization_name
            search_params.append(f"name: {self.q_organization_name}")
        if self.q_organization_domains:
            payload["q_organization_domains"] = self.q_organization_domains
            search_params.append(f"domains: {self.q_organization_domains}")
        if self.q_organization_locations:
            payload["q_organization_locations"] = self.q_organization_locations
            search_params.append(f"locations: {self.q_organization_locations}")
        if self.q_organization_industries:
            payload["q_organization_industries"] = self.q_organization_industries
            search_params.append(f"industries: {self.q_organization_industries}")
        if self.q_organization_employee_count_ranges:
            payload["q_organization_employee_count_ranges"] = self.q_organization_employee_count_ranges
            search_params.append(f"employee_count: {self.q_organization_employee_count_ranges}")
        if self.q_organization_revenue_ranges:
            payload["q_organization_revenue_ranges"] = self.q_organization_revenue_ranges
            search_params.append(f"revenue: {self.q_organization_revenue_ranges}")
        if self.q_organization_funding_stages:
            payload["q_organization_funding_stages"] = self.q_organization_funding_stages
            search_params.append(f"funding_stages: {self.q_organization_funding_stages}")
        if self.q_organization_technologies:
            payload["q_organization_technologies"] = self.q_organization_technologies
            search_params.append(f"technologies: {self.q_organization_technologies}")

        # Log search details
        self.log("=== APOLLO ORGANIZATION SEARCH STARTED ===")
        self.log(f"URL: {url}")
        self.log(f"Page: {self.page}, Per Page: {self.per_page}")
        self.log(f"Enrich Domain: {self.enrich_domain}")
        if search_params:
            self.log(f"Search Parameters: {', '.join(search_params)}")
        else:
            self.log("No specific search parameters provided - using default search")
        self.log(f"Total payload parameters: {len(payload)}")
        self.log(f"Payload enviado para Apollo API: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        try:
            self.log("Sending request to Apollo API...")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            json_data = response.json()

            self.log(f"Response status: {response.status_code}")
            self.log(f"Response received successfully")

            if not json_data.get("organizations"):
                self.log("No organizations found in response")
                return DataFrame(pd.DataFrame({"message": ["No organizations found."]}))

            organizations_count = len(json_data["organizations"])
            self.log(f"Found {organizations_count} organizations")
            
            # Log first organization details for debugging
            if organizations_count > 0:
                first_org = json_data["organizations"][0]
                self.log(f"First organization: {first_org.get('name', 'N/A')} - {first_org.get('domain', 'N/A')}")

            df = pd.DataFrame(json_data["organizations"])
            self.log("=== APOLLO ORGANIZATION SEARCH COMPLETED ===")
            return DataFrame(df)

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {e}"
            self.log(error_msg)
            self.status = error_msg
            return DataFrame(pd.DataFrame({"error": [str(e)]}))

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.log(error_msg)
            self.status = error_msg
            return DataFrame(pd.DataFrame({"error": [str(e)]})) 