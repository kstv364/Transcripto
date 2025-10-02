# Transcript Summarizer using Langgraph and Llama3

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/kaustavchanda/Transcripto)


# Live Deployment: 

Access the application here: 🚀 [Transcripto on Hugging Face Spaces](https://huggingface.co/spaces/kaustavchanda/Transcripto) 🔗

A scalable transcript summarizer application built with Python, Ollama API, LLaMA3, LangChain, and Gradio. This application can handle long transcriptions that exceed the context window by chunking and processing them efficiently.

## Features

- 📄 Upload .vtt transcript files
- 🤖 AI-powered summarization using LLaMA3 via Ollama
- 🔄 Handles long transcripts with intelligent chunking
- 🎯 Multi-level summarization (chunk-level and final summary)
- 🐳 Fully containerized with Docker
- 🎨 Modern Gradio web interface
- 🔧 Modular and extensible architecture
- ⚙️ Configurable via environment variables
- 📝 Configurable logging levels for debugging

## Architecture

```
transcripter/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── summarizer.py      # Main summarization logic
│   │   ├── chunker.py         # Text chunking strategies
│   │   └── vtt_parser.py      # VTT file parsing
│   ├── services/
│   │   ├── __init__.py
│   │   └── ollama_service.py  # Ollama API integration
│   ├── ui/
│   │   ├── __init__.py
│   │   └── gradio_app.py      # Gradio interface
│   └── utils/
│       ├── __init__.py
│       └── config.py          # Configuration management
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── main.py
└── setup.py
```

## Quick Start

### Prerequisites

- Python 3.8+ (tested with Python 3.13)
- Docker & Docker Compose (for containerized deployment)
- Ollama running locally with LLaMA3 model

### Setup Development Environment

#### Option 1: Automated Setup (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd c:\Workspace\Personal\transcripter
   ```

2. **Run the automated setup script:**
   ```bash
   setup.bat
   ```
   
   This script will:
   - Create a virtual environment
   - Install all dependencies
   - Check Ollama connectivity
   - Provide setup status

#### Option 2: Manual Setup

1. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Install dependencies (choose one):**
   
   **Full Installation (Recommended):**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Minimal Installation (if you face dependency issues):**
   ```bash
   pip install -r requirements-minimal.txt
   ```

4. **Ensure Ollama is running with LLaMA3:**
   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

5. **Run the application:**
   ```bash
   python main.py
   ```

6. **Access the web interface:**
   Open http://localhost:7860 in your browser

### Using Docker

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose -f docker/docker-compose.yml up --build
   ```

2. **Access the application:**
   Open http://localhost:7860 in your browser

## Usage

1. **Upload VTT File:** Click on the file upload area and select your .vtt transcript file
2. **Configure Settings:** Adjust chunk size and overlap settings if needed
3. **Generate Summary:** Click "Generate Summary" to process the transcript
4. **Review Results:** View the generated summary and processing statistics

## Configuration

The application can be configured through environment variables or by creating a `.env` file in the project root:

- `OLLAMA_BASE_URL`: Ollama API base URL (default: http://localhost:11434)
- `MODEL_NAME`: LLaMA model name (default: llama3.1:8b)
- `CHUNK_SIZE`: Maximum tokens per chunk (default: 2000)
- `CHUNK_OVERLAP`: Token overlap between chunks (default: 200)
- `GRADIO_PORT`: Gradio server port (default: 7860)
- `MAX_CONCURRENT_REQUESTS`: Maximum concurrent API requests (default: 3)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 300)
- `TEMPERATURE`: Temperature for text generation (default: 0.3)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR, or CRITICAL (default: INFO)

### Environment File Setup

Copy the example environment file and modify as needed:
```bash
cp .env.example .env
```

Then edit `.env` with your preferred settings:
```env
# Example .env configuration
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.1:8b
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
TEMPERATURE=0.3
GRADIO_PORT=7860
MAX_CONCURRENT_REQUESTS=3
REQUEST_TIMEOUT=300
LOG_LEVEL=INFO
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Test specific modules
python -m pytest tests/test_config.py -v        # Test configuration loading
python -m pytest tests/test_chunker.py -v       # Test text chunking
python -m pytest tests/test_vtt_parser.py -v    # Test VTT parsing
python -m pytest tests/test_ollama_service.py -v # Test Ollama integration
```

### Testing Configuration
To verify your environment configuration is working correctly:
```bash
python -c "from src.utils.config import Config; c = Config(); print(f'Loaded config: {c.dict()}')"
```

## License

MIT License
