"""
Google Image Analyzer Component

## Description

The **Google Image Analyzer** is a LangFlow component that allows analyzing images using the powerful Google Cloud Vision APIs. This component offers a wide range of image analysis functionalities, including object detection, OCR, facial analysis, landmark detection and much more.

## Features

### Available Analysis Types

1. **LABEL_DETECTION** - Identifies objects, concepts and labels in the image
2. **TEXT_DETECTION** - Detects and extracts text (basic OCR)
3. **DOCUMENT_TEXT_DETECTION** - Advanced OCR for structured documents
4. **FACE_DETECTION** - Detects faces and emotions
5. **LANDMARK_DETECTION** - Identifies tourist attractions and famous landmarks
6. **LOGO_DETECTION** - Detects brand logos
7. **OBJECT_LOCALIZATION** - Localizes specific objects with coordinates
8. **SAFE_SEARCH_DETECTION** - Analyzes potentially inappropriate content
9. **IMAGE_PROPERTIES** - Analyzes properties like dominant colors
10. **WEB_DETECTION** - Finds similar images on the web
11. **CROP_HINTS** - Suggests ideal crops for the image
12. **ALL_FEATURES** - Executes all available analyses

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud project with billing enabled
2. **Enable Vision API**: The Cloud Vision API must be enabled for your project
   - Go to: https://console.cloud.google.com/apis/library/vision.googleapis.com
   - Click "Enable" for your project
3. **API Key**: Generate an API key with Vision API permissions
   - Go to: https://console.cloud.google.com/apis/credentials
   - Create credentials → API Key
   - Restrict the key to Vision API for security

## Required Inputs

### Required
- **Google API Key**: Your Google Cloud API key
- **Project ID**: Your Google Cloud project ID
- **Image File** OR **Image URL**: Image for analysis (file or URL)

### Optional
- **Analysis Type**: Type of analysis to perform (default: LABEL_DETECTION)
- **Max Results**: Maximum number of results (default: 10)
- **Language Hints**: Languages for text detection (e.g., "en,pt,es")
- **Enable Text Detection Confidence**: Include confidence scores

## Supported Image Formats

- **JPG/JPEG**
- **PNG**
- **GIF**
- **WEBP**
- **BMP**
- **PDF** (for document OCR)
- **TIFF**

## Usage Examples

### 1. Basic Label Analysis
```
Configuration:
- image_file: "dog_photo.jpg"
- analysis_type: "LABEL_DETECTION"
- max_results: 5

Expected result:
{
  "results": {
    "labels": [
      {"description": "Dog", "score": 0.98, "confidence": 0.95},
      {"description": "Animal", "score": 0.96, "confidence": 0.92},
      {"description": "Pet", "score": 0.94, "confidence": 0.90}
    ]
  }
}
```

### 2. OCR - Text Extraction
```
Configuration:
- image_file: "document.jpg"
- analysis_type: "TEXT_DETECTION"
- language_hints: "pt,en"

Expected result:
{
  "results": {
    "text": {
      "full_text": "Complete text extracted from document...",
      "individual_words": [
        {"text": "Word", "confidence": 0.99, "bounding_box": {...}}
      ]
    }
  }
}
```

### 3. Face Detection with Emotions
```
Configuration:
- image_file: "people.jpg"
- analysis_type: "FACE_DETECTION"
- max_results: 10

Expected result:
{
  "results": {
    "faces": [
      {
        "detection_confidence": 0.98,
        "joy_likelihood": "VERY_LIKELY",
        "sorrow_likelihood": "VERY_UNLIKELY",
        "anger_likelihood": "UNLIKELY",
        "surprise_likelihood": "POSSIBLE",
        "bounding_box": {...}
      }
    ]
  }
}
```

## Response Structure

The component returns a Data object with the following structure:
```
{
  "analysis_type": "ANALYSIS_TYPE",
  "results": {
    # Formatted results based on analysis type
  },
  "raw_response": {
    # Complete Google API response (for debugging)
  },
  "image_source": "file" | "url"
}
```

## Error Handling

The component includes robust error handling for:
- **Authentication issues**: Invalid API key or insufficient permissions
- **Quota limits**: Excessive requests
- **Image format**: Unsupported files
- **File size**: Images too large
- **Connectivity**: Network issues

## Practical Use Cases

### 1. **E-commerce**
- Automatic product categorization
- Logo detection for authenticity verification
- Image quality analysis

### 2. **Documents**
- Document digitization and OCR
- Form data extraction
- Multilingual document analysis

### 3. **Security**
- Inappropriate content detection
- Identity verification through documents
- Image monitoring

### 4. **Marketing**
- Image engagement analysis
- Brand mention detection
- Visual content analysis

### 5. **Tourism**
- Automatic landmark identification
- Travel photo metadata generation
- Destination analysis

## Limitations

1. **File size**: Maximum 20MB per image
2. **Rate limits**: Limited by your Google Cloud account quota
3. **Resolution**: Better performance with high-quality images
4. **Languages**: Variable support depending on functionality

## Costs

Using this component results in charges to your Google Cloud account based on Vision API pricing (https://cloud.google.com/vision/pricing). Monitor your usage through the Google Cloud Console.

## Troubleshooting

### Authentication Error
- Check if the API key is correct
- Confirm Vision API is enabled in the project
- Verify API key permissions

### Quota Error
- Monitor usage in Google Cloud Console
- Consider increasing limits if necessary
- Implement retry logic with backoff

### Low Quality Results
- Use high-resolution images
- Ensure good lighting and contrast
- For OCR, use images with clear and readable text

## Support

For component-related issues, consult:
- Official Vision API documentation (https://cloud.google.com/vision/docs)
- API Status (https://status.cloud.google.com/)
- Google Cloud Support (https://cloud.google.com/support)
"""

from lfx.custom import Component
from lfx.io import StrInput, MessageInput, SecretStrInput, IntInput, BoolInput, DropdownInput, FileInput, Output
from lfx.schema import Data
import requests
import base64
import mimetypes
from typing import List, Dict, Any


class GoogleImageAnalyzerComponent(Component):
    display_name = "Google Image Analyzer"
    description = "Analyze images using Google Cloud Vision API for OCR, object detection, labels, face detection and more."
    icon = "GoogleGenerativeAI"
    name = "GoogleImageAnalyzerComponent"
    beta = True

    inputs = [
        FileInput(
            name="image_file",
            display_name="Image File",
            info="Image file to analyze (JPG, PNG, GIF, WEBP, BMP, PDF, TIFF).",
            file_types=["jpg", "jpeg", "png", "gif", "webp", "bmp", "pdf", "tiff"],
            required=False,
        ),
        StrInput(
            name="image_url",
            display_name="Image URL",
            info="URL of the image to analyze (if no file is provided).",
            required=False,
        ),
        SecretStrInput(
            name="api_key",
            display_name="Google API Key",
            info="Your Google Cloud API key with Vision API access.",
            required=True,
            real_time_refresh=True,
        ),
        StrInput(
            name="project_id",
            display_name="Project ID",
            info="Your Google Cloud project ID.",
            required=True,
        ),
        DropdownInput(
            name="analysis_type",
            display_name="Analysis Type",
            info="Type of analysis to perform on the image.",
            options=[
                "LABEL_DETECTION",
                "TEXT_DETECTION", 
                "DOCUMENT_TEXT_DETECTION",
                "FACE_DETECTION",
                "LANDMARK_DETECTION",
                "LOGO_DETECTION",
                "OBJECT_LOCALIZATION",
                "SAFE_SEARCH_DETECTION",
                "IMAGE_PROPERTIES",
                "WEB_DETECTION",
                "PRODUCT_SEARCH",
                "CROP_HINTS",
                "ALL_FEATURES"
            ],
            value="LABEL_DETECTION",
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of results to return for applicable features.",
            value=10,
        ),
        StrInput(
            name="language_hints",
            display_name="Language Hints",
            info="Language hints for text detection (comma-separated, e.g., 'en,pt,es').",
            value="",
        ),
        BoolInput(
            name="enable_text_detection_confidence",
            display_name="Enable Text Detection Confidence",
            info="Include confidence scores for text detection.",
            value=True,
        ),
    ]

    outputs = [
        Output(display_name="Analysis Results", name="analysis_results", method="analyze_image"),
    ]

    field_order = [
        "image_file", "image_url", "api_key", "project_id", "analysis_type",
        "max_results", "language_hints", "enable_text_detection_confidence"
    ]

    def _get_analysis_features(self) -> List[Dict[str, Any]]:
        """Get the analysis features based on selected analysis type"""
        
        if self.analysis_type == "ALL_FEATURES":
            return [
                {"type": "LABEL_DETECTION", "maxResults": self.max_results},
                {"type": "TEXT_DETECTION"},
                {"type": "DOCUMENT_TEXT_DETECTION"},
                {"type": "FACE_DETECTION", "maxResults": self.max_results},
                {"type": "LANDMARK_DETECTION", "maxResults": self.max_results},
                {"type": "LOGO_DETECTION", "maxResults": self.max_results},
                {"type": "OBJECT_LOCALIZATION", "maxResults": self.max_results},
                {"type": "SAFE_SEARCH_DETECTION"},
                {"type": "IMAGE_PROPERTIES"},
                {"type": "WEB_DETECTION", "maxResults": self.max_results},
                {"type": "CROP_HINTS", "maxResults": self.max_results},
            ]
        else:
            feature = {"type": self.analysis_type}
            
            # Add maxResults for features that support it
            if self.analysis_type in [
                "LABEL_DETECTION", "FACE_DETECTION", "LANDMARK_DETECTION", 
                "LOGO_DETECTION", "OBJECT_LOCALIZATION", "WEB_DETECTION", "CROP_HINTS"
            ]:
                feature["maxResults"] = self.max_results
            
            return [feature]

    def _prepare_image_content(self) -> Dict[str, Any]:
        """Prepare image content for the API request"""
        
        if self.image_file:
            # Handle file input - multiple possible types
            try:
                # Case 1: File object with read() method
                if hasattr(self.image_file, 'read'):
                    file_content = self.image_file.read()
                    if isinstance(file_content, str):
                        # If it's already base64
                        image_content = file_content
                    else:
                        # Convert bytes to base64
                        image_content = base64.b64encode(file_content).decode('utf-8')
                
                # Case 2: String input (could be file path or base64)
                elif isinstance(self.image_file, str):
                    # Check if it looks like a file path
                    if self.image_file.startswith('/') or '\\' in self.image_file or '.' in self.image_file:
                        # Treat as file path
                        try:
                            with open(self.image_file, 'rb') as f:
                                file_content = f.read()
                            image_content = base64.b64encode(file_content).decode('utf-8')
                        except FileNotFoundError:
                            # If file not found, treat as base64 string
                            image_content = self.image_file
                    else:
                        # Treat as base64 string
                        image_content = self.image_file
                
                # Case 3: Bytes content
                elif isinstance(self.image_file, bytes):
                    image_content = base64.b64encode(self.image_file).decode('utf-8')
                
                # Case 4: Other types, try to convert to string
                else:
                    image_content = str(self.image_file)
                
                return {"content": image_content}
                
            except Exception as e:
                raise ValueError(f"Error processing image file: {str(e)}. File type: {type(self.image_file)}")
        
        elif self.image_url:
            # Handle URL input
            return {"source": {"imageUri": self.image_url}}
        
        else:
            raise ValueError("Either image_file or image_url must be provided")

    def _build_payload(self) -> Dict[str, Any]:
        """Build the API payload"""
        
        # Prepare image content
        image_content = self._prepare_image_content()
        
        # Get analysis features
        features = self._get_analysis_features()
        
        # Build base payload
        payload = {
            "requests": [{
                "image": image_content,
                "features": features
            }]
        }
        
        # Add image context if needed
        image_context = {}
        
        # Add language hints for text detection
        if self.language_hints and any(f["type"] in ["TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION"] for f in features):
            language_list = [lang.strip() for lang in self.language_hints.split(",") if lang.strip()]
            if language_list:
                image_context["languageHints"] = language_list
        
        # Add crop hints parameters - use correct field name
        if any(f["type"] == "CROP_HINTS" for f in features):
            image_context["cropHintsParams"] = {
                "aspectRatios": [1.0, 1.5, 2.0]
            }
        
        # Note: Removed includeGeoResults as it's not a valid field in the current API
        # Geo results are included by default in landmark detection when available
        
        # Add image context if we have any settings
        if image_context:
            payload["requests"][0]["imageContext"] = image_context
        
        return payload

    def _format_results(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the API response into a readable structure"""
        
        if "responses" not in response_data or not response_data["responses"]:
            return {"error": "No responses received from API"}
        
        response = response_data["responses"][0]
        formatted_results = {}
        
        # Handle different types of analysis results
        if "labelAnnotations" in response:
            formatted_results["labels"] = [
                {
                    "description": label["description"],
                    "score": label.get("score", 0),
                    "confidence": label.get("confidence", 0)
                }
                for label in response["labelAnnotations"]
            ]
        
        if "textAnnotations" in response:
            formatted_results["text"] = {
                "full_text": response["textAnnotations"][0]["description"] if response["textAnnotations"] else "",
                "individual_words": [
                    {
                        "text": text["description"],
                        "confidence": text.get("confidence", 0),
                        "bounding_box": text.get("boundingPoly", {})
                    }
                    for text in response["textAnnotations"][1:]  # Skip the first one which is full text
                ]
            }
        
        if "fullTextAnnotation" in response:
            formatted_results["document_text"] = {
                "text": response["fullTextAnnotation"]["text"],
                "pages": len(response["fullTextAnnotation"].get("pages", [])),
                "confidence": response["fullTextAnnotation"].get("confidence", 0)
            }
        
        if "faceAnnotations" in response:
            formatted_results["faces"] = [
                {
                    "detection_confidence": face.get("detectionConfidence", 0),
                    "joy_likelihood": face.get("joyLikelihood", "UNKNOWN"),
                    "sorrow_likelihood": face.get("sorrowLikelihood", "UNKNOWN"),
                    "anger_likelihood": face.get("angerLikelihood", "UNKNOWN"),
                    "surprise_likelihood": face.get("surpriseLikelihood", "UNKNOWN"),
                    "bounding_box": face.get("boundingPoly", {})
                }
                for face in response["faceAnnotations"]
            ]
        
        if "landmarkAnnotations" in response:
            formatted_results["landmarks"] = [
                {
                    "description": landmark["description"],
                    "score": landmark.get("score", 0),
                    "locations": landmark.get("locations", [])
                }
                for landmark in response["landmarkAnnotations"]
            ]
        
        if "logoAnnotations" in response:
            formatted_results["logos"] = [
                {
                    "description": logo["description"],
                    "score": logo.get("score", 0),
                    "bounding_box": logo.get("boundingPoly", {})
                }
                for logo in response["logoAnnotations"]
            ]
        
        if "localizedObjectAnnotations" in response:
            formatted_results["objects"] = [
                {
                    "name": obj["name"],
                    "score": obj.get("score", 0),
                    "bounding_box": obj.get("boundingPoly", {})
                }
                for obj in response["localizedObjectAnnotations"]
            ]
        
        if "safeSearchAnnotation" in response:
            safe_search = response["safeSearchAnnotation"]
            formatted_results["safe_search"] = {
                "adult": safe_search.get("adult", "UNKNOWN"),
                "spoof": safe_search.get("spoof", "UNKNOWN"),
                "medical": safe_search.get("medical", "UNKNOWN"),
                "violence": safe_search.get("violence", "UNKNOWN"),
                "racy": safe_search.get("racy", "UNKNOWN")
            }
        
        if "imagePropertiesAnnotation" in response:
            props = response["imagePropertiesAnnotation"]
            formatted_results["image_properties"] = {
                "dominant_colors": [
                    {
                        "color": color["color"],
                        "score": color.get("score", 0),
                        "pixel_fraction": color.get("pixelFraction", 0)
                    }
                    for color in props.get("dominantColors", {}).get("colors", [])
                ]
            }
        
        if "webDetection" in response:
            web = response["webDetection"]
            formatted_results["web_detection"] = {
                "web_entities": [
                    {
                        "description": entity.get("description", ""),
                        "score": entity.get("score", 0)
                    }
                    for entity in web.get("webEntities", [])
                ],
                "similar_images": [img.get("url", "") for img in web.get("visuallySimilarImages", [])],
                "pages_with_matching_images": [page.get("url", "") for page in web.get("pagesWithMatchingImages", [])]
            }
        
        if "cropHintsAnnotation" in response:
            formatted_results["crop_hints"] = [
                {
                    "bounding_box": hint.get("boundingPoly", {}),
                    "confidence": hint.get("confidence", 0),
                    "importance_fraction": hint.get("importanceFraction", 0)
                }
                for hint in response["cropHintsAnnotation"].get("cropHints", [])
            ]
        
        # Handle errors
        if "error" in response:
            formatted_results["error"] = response["error"]
        
        return formatted_results

    def analyze_image(self) -> Data:
        """Perform image analysis using Google Vision API"""
        
        # Validate inputs
        if not self.image_file and not self.image_url:
            error_msg = "Either image_file or image_url must be provided"
            self.status = error_msg
            return Data(data={"error": error_msg})
        
        # Build the endpoint URL with API key as query parameter
        endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            # Build payload
            payload = self._build_payload()
            
            self.log(f"Performing {self.analysis_type} analysis on image")
            
            # Make API request
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Format results
            formatted_results = self._format_results(response_data)
            
            # Prepare final result
            result_data = {
                "analysis_type": self.analysis_type,
                "results": formatted_results,
                "raw_response": response_data,  # Include raw response for debugging
                "image_source": "file" if self.image_file else "url"
            }
            
            # Count total findings
            total_findings = 0
            for key, value in formatted_results.items():
                if isinstance(value, list):
                    total_findings += len(value)
                elif isinstance(value, dict) and "individual_words" in value:
                    total_findings += len(value["individual_words"])
            
            self.status = f"Analysis completed: {total_findings} findings using {self.analysis_type}"
            return Data(data=result_data)
            
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_code = error_data.get('error', {}).get('code', 'Unknown')
                    error_message = error_data.get('error', {}).get('message', str(e))
                    
                    # Provide user-friendly messages for common errors
                    if error_code == 403 and 'SERVICE_DISABLED' in str(error_data):
                        user_message = (
                            "❌ **Google Cloud Vision API is not enabled**\n\n"
                            "**To fix this:**\n"
                            "1. Go to Google Cloud Console\n"
                            "2. Enable the Cloud Vision API for your project\n"
                            "3. Wait a few minutes for activation\n"
                            "4. Try again\n\n"
                            f"**Quick link:** https://console.developers.google.com/apis/api/vision.googleapis.com/overview?project={self.project_id}\n\n"
                            f"Original error: {error_message}"
                        )
                    elif error_code == 401:
                        user_message = (
                            "❌ **Authentication Error**\n\n"
                            "**Possible causes:**\n"
                            "• Invalid API Key\n"
                            "• API Key doesn't have Vision API permissions\n"
                            "• Project ID mismatch\n\n"
                            f"Original error: {error_message}"
                        )
                    elif error_code == 400:
                        user_message = (
                            "❌ **Bad Request**\n\n"
                            "**Possible causes:**\n"
                            "• Invalid image format or size\n"
                            "• Malformed request parameters\n"
                            "• Unsupported analysis type\n\n"
                            f"Original error: {error_message}"
                        )
                    else:
                        user_message = f"Request error: {e.response.status_code} {e.response.reason} for url: {e.response.url} - {error_data}"
                    
                    error_msg = f"Google Vision API Error: {user_message}"
                except (ValueError, KeyError):
                    error_msg = f"Request error: {str(e)}"
            else:
                error_msg = f"Request error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg})
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg}) 
