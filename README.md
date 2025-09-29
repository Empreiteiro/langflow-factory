# 🏭 Langflow Factory

**Custom Component Library for Langflow - Extending AI Workflow Capabilities**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Langflow](https://img.shields.io/badge/Langflow-Compatible-green.svg)](https://langflow.org/)

## 🌟 Overview

Langflow Factory is a comprehensive collection of custom components designed to extend Langflow's capabilities with powerful integrations, data processing tools, and AI-powered generators. Built with production-ready patterns and extensive error handling.

## 🚀 Features

### 🔗 **API Integrations**
- **Google Cloud Platform**: BigQuery, Cloud Scheduler, Drive integration
- **WhatsApp/Evolution API**: Complete messaging automation
- **Google Sheets**: Read, write, and query operations
- **Apollo**: Organization search capabilities
- **Astra DB**: Vector database operations

### 📊 **Data Processing**
- **Enhanced DataFrame Operations**: Advanced data manipulation
- **File Processing**: Multi-format support with encoding detection
- **Structured Output**: Type-safe data transformation
- **Data Validation**: Robust input/output validation

### 🎨 **AI Generators**
- **Image Generation**: OpenAI DALL-E, Google Imagen
- **Audio Generation**: ElevenLabs, OpenAI TTS
- **Text Processing**: Advanced natural language operations

### 🛠️ **Utilities**
- **API Request Builder**: Dynamic HTTP client with authentication
- **Conditional Router**: Smart flow control
- **Dynamic UI Components**: Real-time field updates

## 📁 Project Structure

```
langflow-factory/
├── .cursor/                    # Development rules and guidelines
│   ├── index.mdc              # Project-wide Cursor rules
│   └── rules/                 # Context-specific rules
├── components/                # Custom Langflow components
│   ├── api_request/           # HTTP request builders
│   ├── audio_management/      # Audio generation components
│   ├── gcp/                   # Google Cloud integrations
│   ├── google_sheets/         # Sheets API components
│   ├── image_generators/      # Image generation tools
│   └── [other categories]/
├── flows/                     # Example flows and configurations
├── tests/                     # Component testing framework
└── scripts/                   # Utility scripts
```

## 🎯 Getting Started

### 📋 Templates Available
Ready-to-use Langflow templates are available at: **[https://github.com/Empreiteiro/langflow-templates](https://github.com/Empreiteiro/langflow-templates)**

This repository includes 56+ pre-built templates organized by:
- **AI Patterns**: Agentic RAG, Document Intelligence, Multi-Modal Processing, Structured Output Generation
- **Business Functions**: Data Analytics, Financial Services, Sales & Marketing Automation, Social & Brand Intelligence, Programming & Developer Productivity

### Prerequisites
- Python 3.8+
- Langflow installed and running
- Required API keys for integrations

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Empreiteiro/langflow-factory.git
cd langflow-factory
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Add components to Langflow:**
   - Copy component files to your Langflow custom components directory
   - Or load directly through Langflow's component upload feature

### Quick Start Example

```python
# Example: Using the Enhanced API Request component
from components.api_request.enchanced_api_request import EnhancedAPIRequest

component = EnhancedAPIRequest()
component.url = "https://api.example.com/data"
component.method = "GET"
result = component.make_request()
```

## 🔧 Component Categories

### 📡 **API & External Services**
- `api_request_builder.py` - Dynamic HTTP request construction
- `enchanced_api_request.py` - Advanced API client with retry logic
- `apollo_organization_search.py` - Company data retrieval
- `astra_db.py` - Vector database operations

### ☁️ **Google Cloud Platform**
- `cloud_scheduler` - Automated job scheduling
- `enchanced_big_query.py` - BigQuery data operations
- `google_drive_uploader.py` - File upload automation
- `google_sheets/` - Complete Sheets API integration

### 💬 **Communication**
- `audio_management/` - Voice and audio generation
- `whatsapp_evolution.py` - WhatsApp automation
- `telegram.py` - Telegram bot integration

### 🎥 **Multi-Modal Processing**
- `multi-modal_input.py` - Audio, video, and image processing with AI analysis
  - YouTube video download and analysis
  - Audio transcription using OpenAI Whisper
  - Image analysis using GPT-4V
  - Supports direct URLs, YouTube, and Google Drive links

### 📊 **Data Processing**
- `core_data_operations.py` - Advanced data manipulation
- `dataFrame_operations` - Pandas DataFrame utilities
- `enchanced_structured_output.py` - Type-safe outputs

## 🧪 Testing

Run the test suite to ensure components work correctly:

```bash
# Run all tests
python -m pytest tests/

# Run specific component tests
python -m pytest tests/test_api_request.py

# Test YouTube download functionality
python scripts/test_youtube_download.py
```

## 🔧 Troubleshooting

### YouTube Download Issues

If you encounter "Error downloading video from URL: Failed to download media from URL: Failed to download from YouTube: No file downloaded", follow these steps:

1. **Install yt-dlp:**
```bash
pip install yt-dlp
```

2. **Install FFmpeg (required for video processing):**
   - **Windows:** `winget install FFmpeg` or download from https://ffmpeg.org/download.html
   - **Mac:** `brew install ffmpeg`
   - **Linux:** `sudo apt install ffmpeg`

3. **Run the installation script:**
```bash
python scripts/install_dependencies.py
```

4. **Test the functionality:**
```bash
python scripts/test_youtube_download.py
```

5. **Common issues:**
   - **Private videos:** YouTube private videos cannot be downloaded
   - **Age-restricted content:** May require authentication
   - **Region restrictions:** Some videos are not available in certain regions
   - **Network issues:** Check your internet connection
   - **yt-dlp version:** Ensure you have the latest version: `pip install --upgrade yt-dlp`

## 📚 Documentation

### Component Development Guidelines
- Follow the patterns in `.cursor/rules/langflow-components.mdc`
- Use proper error handling with `self.log()`
- Implement input validation
- Return structured Data/Message/DataFrame objects

### Flow Development
- Reference `.cursor/rules/flow-development.mdc`
- Design for reusability and modularity
- Include proper error handling paths

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-component`)
3. Follow the development guidelines in `.cursor/rules/`
4. Add tests for new components
5. Commit with descriptive messages
6. Push and create a Pull Request

## 📋 Component Checklist

When creating new components:
- [ ] Inherits from `Component`
- [ ] Implements proper error handling
- [ ] Uses `self.log()` for logging
- [ ] Includes input validation
- [ ] Has comprehensive docstrings
- [ ] Includes example usage
- [ ] Has corresponding tests
- [ ] Follows naming conventions

## 🔐 Security

- Store API keys securely using Langflow's secret management
- Validate all inputs to prevent injection attacks
- Use HTTPS for external API calls
- Follow the security guidelines in component documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Langflow](https://langflow.org/) - The amazing low-code AI platform
- [DataStax](https://www.datastax.com/) - For Langflow development and support
- All contributors who help improve this component library

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Empreiteiro/langflow-factory/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Empreiteiro/langflow-factory/discussions)
- **Documentation**: Check the `.cursor/rules/` directory for development guidelines

---

**Made with ❤️ for the Langflow community** 