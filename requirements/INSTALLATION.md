# RAG Pipeline Installation Guide

## Environment Requirements

- Python 3.8 or higher
- pip package manager

## Quick Installation

### Method 1: Using Simplified Dependencies File (Recommended)

```bash
pip install -r requirements_simple.txt
```

### Method 2: Using Complete Dependencies File

```bash
pip install -r requirements.txt
```

### Method 3: Manual Installation of Core Packages

```bash
# Install core packages
pip install haystack-ai
pip install "datasets>=3.6.0"
pip install "sentence-transformers>=4.1.0"
pip install accelerate
pip install python-dotenv
pip install tqdm
pip install cohere
pip install openai
```

## Environment Configuration

1. Create `.env` file in project root directory:

```env
COHERE_API_KEY=your_cohere_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
CO_API_URL=https://api.cohere.ai/v1
```

2. Replace `your_cohere_api_key_here` and `your_openai_api_key_here` with your actual API keys.

## API Key Acquisition

### Cohere API Key
1. Visit [Cohere Dashboard](https://dashboard.cohere.ai/)
2. Register and login
3. Get your key from the API Keys page

### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Register and login
3. Create a new key in the API Keys page

## Verify Installation

Run the following Python code to verify installation:

```python
# Test core imports
from haystack import Pipeline
from haystack_integrations.components.embedders.cohere import CohereDocumentEmbedder
from dotenv import load_dotenv
import os

print("✅ All core packages installed successfully!")

# Test environment variables
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if cohere_key and openai_key:
    print("✅ API keys configured successfully!")
else:
    print("⚠️ Please check API key configuration in .env file")
```

## Common Issues

### 1. Installation Failures

If you encounter installation issues, try:

```bash
# Upgrade pip
pip install --upgrade pip

# Use Tsinghua mirror (for Chinese users)
pip install -r requirements_simple.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. Jupyter Environment

If running in Jupyter Notebook, ensure installation:

```bash
pip install jupyter ipykernel
```

### 3. GPU Support

If you need GPU acceleration (optional), install corresponding PyTorch version:

```bash
# CUDA version (choose based on your CUDA version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Project Structure

```
POLICY-ANALYSIS/
├── incremental_indexing_rag.ipynb  # Main notebook
├── files/
│   └── index_table.json           # Data file
├── outputs/                       # Output directory
├── requirements.txt               # Complete dependencies
├── requirements_simple.txt        # Simplified dependencies
├── INSTALLATION.md               # This file
└── .env                          # Environment variables (needs creation)
```

## Usage Instructions

1. Ensure all dependencies are installed
2. Configure `.env` file
3. Open `incremental_indexing_rag.ipynb`
4. Run all cells in order

## Support

If you encounter issues, please check:
1. Python version meets requirements
2. All dependencies are correctly installed
3. API keys are correctly configured
4. Network connection is normal
