from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output, IntInput, BoolInput
from langflow.schema import DataFrame
import requests
import pandas as pd
import time


class EnhancedBusinessSearchComponent(Component):
    display_name = "Business Search"
    description = "Search for businesses and get detailed information including phone numbers, hours, website, and more using Google Maps Places API."
    icon = "maps"
    name = "EnhancedBusinessSearch"

    field_order = ["api_key", "business_type", "city", "max_results", "include_details"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Your Google Maps API key with Places API (New) enabled.",
            required=True,
        ),
        StrInput(
            name="business_type",
            display_name="Business Type",
            info="Type of business (e.g., restaurant, hospital, bookstore).",
            required=True,
            tool_mode=True        
        ),
        StrInput(
            name="city",
            display_name="City",
            info="City to search in (e.g., New York, Paris).",
            required=True,
            tool_mode=True        
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of businesses to return (default: 10).",
            value=100,
        ),
        BoolInput(
            name="include_details",
            display_name="Include Detailed Info",
            info="Whether to fetch detailed information for each business (slower but more complete).",
            value=True,
        ),
    ]

    outputs = [
        Output(name="results", display_name="Enhanced Business Results", method="search_businesses")
    ]

    def get_place_details(self, place_id: str) -> dict:
        """Get detailed information for a specific place ID."""
        try:
            url = f"https://places.googleapis.com/v1/places/{place_id}"
            params = {
                "fields": "displayName,formattedAddress,internationalPhoneNumber,rating,userRatingCount,websiteUri,regularOpeningHours,priceLevel,types,businessStatus"
            }
            headers = {
                "X-Goog-Api-Key": self.api_key
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract opening hours
                opening_hours = ""
                if "regularOpeningHours" in data:
                    periods = data["regularOpeningHours"].get("weekdayDescriptions", [])
                    opening_hours = " | ".join(periods)
                
                # Extract business types
                types = data.get("types", [])
                business_types = ", ".join(types[:3])  # Limit to first 3 types
                
                return {
                    "phone": data.get("internationalPhoneNumber", ""),
                    "website": data.get("websiteUri", ""),
                    "opening_hours": opening_hours,
                    "price_level": data.get("priceLevel", ""),
                    "business_types": business_types,
                    "business_status": data.get("businessStatus", "")
                }
            else:
                self.log(f"Details fetch failed for {place_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            self.log(f"Details fetch exception for {place_id}: {str(e)}")
            return {}

    def search_businesses(self) -> DataFrame:
        try:
            query = f"{self.business_type} in {self.city}"
            url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.id,places.internationalPhoneNumber"
            }
            body = {
                "textQuery": query,
                "maxResultCount": min(self.max_results, 20)  # API limit is 20
            }

            self.log(f"Searching for: {query}")
            response = requests.post(url, headers=headers, json=body, timeout=15)
            
            if response.status_code != 200:
                error_info = response.json().get("error", {})
                message = error_info.get("message", response.text)
                self.status = f"Google API Error: {message}"
                return DataFrame(pd.DataFrame({"error": [self.status]}))

            places = response.json().get("places", [])
            if not places:
                return DataFrame(pd.DataFrame({"message": ["No businesses found."]}))

            results = []
            total_places = len(places)
            
            self.log(f"Found {total_places} businesses. Processing...")
            
            for i, place in enumerate(places):
                self.log(f"Processing business {i+1}/{total_places}")
                
                # Basic information from search
                place_id = place.get("id", "")
                basic_info = {
                    "name": place.get("displayName", {}).get("text", ""),
                    "address": place.get("formattedAddress", ""),
                    "rating": place.get("rating", ""),
                    "user_ratings_total": place.get("userRatingCount", ""),
                    "place_id": place_id,
                    "phone": place.get("internationalPhoneNumber", ""),
                    "website": "",
                    "opening_hours": "",
                    "price_level": "",
                    "business_types": "",
                    "business_status": ""
                }

                # Get detailed information if requested and place_id exists
                if self.include_details and place_id:
                    self.log(f"Fetching details for: {basic_info['name']}")
                    details = self.get_place_details(place_id)
                    
                    # Merge details with basic info
                    basic_info.update(details)
                    
                    # Add small delay to respect API rate limits
                    time.sleep(0.1)

                results.append(basic_info)

            df = pd.DataFrame(results)
            self.log(f"Returning DataFrame with {len(df)} rows and columns: {list(df.columns)}")
            return DataFrame(df)

        except Exception as e:
            self.status = f"Request failed: {str(e)}"
            self.log(self.status)
            return DataFrame(pd.DataFrame({"error": [self.status]})) 