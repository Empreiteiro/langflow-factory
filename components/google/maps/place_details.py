from lfx.custom import Component
from lfx.io import StrInput, SecretStrInput, Output, BoolInput
from lfx.schema import Data, DataFrame
import requests
import pandas as pd
import json


class GooglePlaceDetailsComponent(Component):
    display_name = "Enhanced Place Details"
    description = "Get comprehensive detailed information about a business using its Google Place ID, including all available fields."
    icon = "mdi-domain"
    name = "GooglePlaceDetails"

    field_order = ["api_key", "place_id", "include_reviews", "include_photos"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Your Google Maps API key with Places API (New) enabled.",
            required=True,
        ),
        StrInput(
            name="place_id",
            display_name="Place ID",
            info="The Place ID of the business you want details for.",
            required=True,
        ),
        BoolInput(
            name="include_reviews",
            display_name="Include Reviews",
            info="Whether to fetch user reviews (adds more API cost).",
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="include_photos",
            display_name="Include Photos",
            info="Whether to fetch photo references (adds more API cost).",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="details", display_name="Enhanced Place Details", method="get_details")
    ]

    def get_details(self) -> DataFrame:
        try:
            url = f"https://places.googleapis.com/v1/places/{self.place_id}"
            
            # Build comprehensive field list
            basic_fields = [
                "displayName", "formattedAddress", "internationalPhoneNumber", 
                "nationalPhoneNumber", "rating", "userRatingCount", "priceLevel",
                "websiteUri", "businessStatus", "types", "googleMapsUri"
            ]
            
            location_fields = [
                "location", "viewport", "addressComponents"
            ]
            
            hours_fields = [
                "regularOpeningHours", "currentOpeningHours", "secondaryOpeningHours"
            ]
            
            service_fields = [
                "delivery", "dineIn", "takeout", "servesBeer", "servesWine", 
                "servesBrunch", "servesLunch", "servesDinner", "servesBreakfast",
                "servesVegetarianFood", "reservable", "goodForChildren", 
                "goodForGroups", "goodForWatchingSports", "restroom"
            ]
            
            accessibility_fields = [
                "accessibilityOptions", "parkingOptions", "paymentOptions"
            ]
            
            optional_fields = []
            if self.include_reviews:
                optional_fields.extend(["reviews", "editorialSummary"])
            if self.include_photos:
                optional_fields.extend(["photos"])
            
            # Combine all fields
            all_fields = basic_fields + location_fields + hours_fields + service_fields + accessibility_fields + optional_fields
            fields_param = ",".join(all_fields)
            
            params = {"fields": fields_param}
            headers = {"X-Goog-Api-Key": self.api_key}

            self.log(f"Requesting comprehensive details for place: {self.place_id}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                error_info = response.json().get("error", {})
                message = error_info.get("message", response.text)
                self.log(f"API Error: {message}")
                return DataFrame(pd.DataFrame({"error": [f"Google API Error: {message}"]}))

            data = response.json()
            result = self.parse_place_data(data)
            
            df = pd.DataFrame([result])
            self.log(f"Returning enhanced place details with {len(df.columns)} fields")
            return DataFrame(df)

        except Exception as e:
            self.log(f"Request failed: {str(e)}")
            return DataFrame(pd.DataFrame({"error": [f"Request failed: {str(e)}"]}))

    def parse_place_data(self, data: dict) -> dict:
        """Parse comprehensive place data from Google Places API response."""
        
        # Basic Information
        result = {
            "place_id": self.place_id,
            "name": data.get("displayName", {}).get("text", ""),
            "formatted_address": data.get("formattedAddress", ""),
            "phone_international": data.get("internationalPhoneNumber", ""),
            "phone_national": data.get("nationalPhoneNumber", ""),
            "website": data.get("websiteUri", ""),
            "google_maps_url": data.get("googleMapsUri", ""),
            "rating": data.get("rating", ""),
            "user_ratings_total": data.get("userRatingCount", ""),
            "price_level": data.get("priceLevel", ""),
            "business_status": data.get("businessStatus", "")
        }
        
        # Business Types
        types = data.get("types", [])
        result["business_types"] = ", ".join(types[:5])  # Limit to first 5 types
        result["primary_type"] = types[0] if types else ""
        
        # Location Information
        location = data.get("location", {})
        result["latitude"] = location.get("latitude", "")
        result["longitude"] = location.get("longitude", "")
        
        # Address Components
        address_components = data.get("addressComponents", [])
        for component in address_components:
            types_list = component.get("types", [])
            if "street_number" in types_list:
                result["street_number"] = component.get("longText", "")
            elif "route" in types_list:
                result["street_name"] = component.get("longText", "")
            elif "locality" in types_list:
                result["city"] = component.get("longText", "")
            elif "administrative_area_level_1" in types_list:
                result["state"] = component.get("shortText", "")
            elif "postal_code" in types_list:
                result["postal_code"] = component.get("longText", "")
            elif "country" in types_list:
                result["country"] = component.get("longText", "")
        
        # Opening Hours
        regular_hours = data.get("regularOpeningHours", {})
        if regular_hours:
            periods = regular_hours.get("weekdayDescriptions", [])
            result["opening_hours"] = " | ".join(periods)
            result["open_now"] = regular_hours.get("openNow", "")
        else:
            result["opening_hours"] = ""
            result["open_now"] = ""
        
        # Service Options
        result["delivery"] = data.get("delivery", "")
        result["dine_in"] = data.get("dineIn", "")
        result["takeout"] = data.get("takeout", "")
        result["reservable"] = data.get("reservable", "")
        result["good_for_children"] = data.get("goodForChildren", "")
        result["good_for_groups"] = data.get("goodForGroups", "")
        result["restroom"] = data.get("restroom", "")
        
        # Food & Drink Services
        result["serves_beer"] = data.get("servesBeer", "")
        result["serves_wine"] = data.get("servesWine", "")
        result["serves_breakfast"] = data.get("servesBreakfast", "")
        result["serves_lunch"] = data.get("servesLunch", "")
        result["serves_dinner"] = data.get("servesDinner", "")
        result["serves_brunch"] = data.get("servesBrunch", "")
        result["serves_vegetarian"] = data.get("servesVegetarianFood", "")
        
        # Accessibility & Parking
        accessibility = data.get("accessibilityOptions", {})
        result["wheelchair_accessible"] = accessibility.get("wheelchairAccessibleEntrance", "")
        
        parking = data.get("parkingOptions", {})
        result["free_parking"] = parking.get("freeParking", "")
        result["paid_parking"] = parking.get("paidParking", "")
        result["street_parking"] = parking.get("streetParking", "")
        result["parking_garage"] = parking.get("paidGarageParking", "")
        
        # Payment Options
        payment = data.get("paymentOptions", {})
        result["accepts_credit_cards"] = payment.get("acceptsCreditCards", "")
        result["accepts_debit_cards"] = payment.get("acceptsDebitCards", "")
        result["accepts_cash_only"] = payment.get("acceptsCashOnly", "")
        result["accepts_nfc"] = payment.get("acceptsNfc", "")
        
        # Reviews (if requested)
        if self.include_reviews and "reviews" in data:
            reviews = data.get("reviews", [])
            if reviews:
                latest_review = reviews[0]
                result["latest_review_text"] = latest_review.get("text", {}).get("text", "")
                result["latest_review_rating"] = latest_review.get("rating", "")
                result["latest_review_author"] = latest_review.get("authorAttribution", {}).get("displayName", "")
                result["total_reviews_found"] = len(reviews)
            
        # Photos (if requested)
        if self.include_photos and "photos" in data:
            photos = data.get("photos", [])
            if photos:
                photo_refs = [photo.get("name", "") for photo in photos[:5]]  # First 5 photos
                result["photo_references"] = " | ".join(photo_refs)
                result["total_photos"] = len(photos)
        
        # Editorial Summary
        editorial = data.get("editorialSummary", {})
        result["editorial_summary"] = editorial.get("text", "")
        
        # Fill empty fields with empty strings for consistent DataFrame structure
        for key, value in result.items():
            if value is None or value == "None":
                result[key] = ""
        
        return result
