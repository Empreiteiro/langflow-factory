from langflow.custom import Component
from langflow.io import MessageInput, SecretStrInput, Output, IntInput, BoolInput
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
        MessageInput(
            name="business_type",
            display_name="Business Type",
            info="Type of business (e.g., restaurant, hospital, bookstore).",
            required=True,
        ),
        MessageInput(
            name="city",
            display_name="City",
            info="City to search in (e.g., New York, Paris).",
            required=True,
        ),
        MessageInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of businesses to return (default: 30).",
            required=False,
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
            # Extract text content from MessageInput
            business_type_text = self.business_type.text if hasattr(self.business_type, 'text') else str(self.business_type)
            city_text = self.city.text if hasattr(self.city, 'text') else str(self.city)
            
            # Extract max_results from MessageInput
            max_results_value = 30  # Default value
            if self.max_results is not None and hasattr(self.max_results, 'text'):
                try:
                    max_results_value = int(self.max_results.text)
                except (ValueError, AttributeError):
                    max_results_value = 30
            
            query = f"{business_type_text} in {city_text}"
            url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.id,places.internationalPhoneNumber,places.location"
            }

            self.log(f"Searching for: {query}")
            all_places = []
            seen_place_ids = set()
            
            # Multiple query variations to get more results
            query_variations = [
                f"{business_type_text} in {city_text}",
                f"{business_type_text} near {city_text}",
                f"{business_type_text} {city_text}",
                f"best {business_type_text} in {city_text}",
                f"top {business_type_text} {city_text}",
            ]
            
            for i, query_variant in enumerate(query_variations):
                if len(all_places) >= max_results_value:
                    break
                    
                self.log(f"Query variation {i+1}/{len(query_variations)}: {query_variant}")
                
                body = {
                    "textQuery": query_variant,
                    "maxResultCount": 20  # API limit is 20 per request
                }

                response = requests.post(url, headers=headers, json=body, timeout=15)
                
                if response.status_code != 200:
                    self.log(f"Query variation {i+1} failed: {response.status_code}")
                    continue

                data = response.json()
                places = data.get("places", [])
                
                # Add unique places only
                for place in places:
                    place_id = place.get("id", "")
                    if place_id and place_id not in seen_place_ids:
                        seen_place_ids.add(place_id)
                        all_places.append(place)
                        
                        if len(all_places) >= max_results_value:
                            break
                
                # Add delay between requests to respect rate limits
                if i < len(query_variations) - 1:
                    time.sleep(0.5)

            if not all_places:
                return DataFrame(pd.DataFrame({"message": ["No businesses found."]}))

            # Limit to the exact number requested
            all_places = all_places[:max_results_value]

            results = []
            total_places = len(all_places)
            
            self.log(f"Found {total_places} businesses. Processing...")
            
            for i, place in enumerate(all_places):
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