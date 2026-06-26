# beta-bot 🧗

A web-based Q&A bot to answer questions about your climbing history. Uses LangChain with local Llama2 (via Ollama) for intelligent, context-aware responses.

## Features

✅ **Local LLM** - Runs Llama2 locally on your machine (no cloud API)  
✅ **Web UI** - Streamlit interface for easy interaction  
✅ **Flexible Data Input** - CSV or JSON climbing data  
✅ **Smart Analytics** - Automatically calculates stats and insights  
✅ **Conversational** - Chat history and context retention  

## Quick Start

### 1. Install Ollama

Download and install from [https://ollama.ai](https://ollama.ai)

### 2. Pull Llama2 Model

Open PowerShell and run:
```powershell
ollama pull llama2
```

This downloads ~3.8 GB and takes 5-10 minutes depending on connection speed.

### 3. Setup Python Environment

Clone this repo and install dependencies:
```powershell
cd beta-bot
pip install -r requirements.txt
```

### 4. Prepare Your Data

Export your climbing data from Mountain Project as CSV or JSON. The expected format for the sample file is a Mountain Project export with columns like:

**CSV Example:**
```csv
Date,Route,Rating,Notes,URL,Pitches,Location,Avg Stars,Your Stars,Style,Lead Style,Route Type,Your Rating,Length,Rating Code
2026-06-02,Roadside Attraction,5.7,,https://www.mountainproject.com/route/105860741/roadside-attraction,2,Kentucky > Red River Gorge > Natural Bridge Region > Graining Fork Nature Preserve (a.k.a. Roadside Crag),3.8,4,Lead,Flash,Trad,,120,1800
```

**JSON Example:**
```json
[
  {
    "route_name": "The Nose",
    "grade": "5.9",
    "area": "El Capitan",
    "date": "2023-06-15",
    "rating": 4.5,
    "type": "Trad",
    "notes": "Great route"
  }
]
```

A sample data file is included at `data/sample_climbing_data.csv`

### 5. Start the Bot

**Terminal 1 - Start Ollama server:**
```powershell
ollama serve
```

**Terminal 2 - Start Streamlit app:**
```powershell
streamlit run app.py
```

This opens your browser at `http://localhost:8501`

### 6. Use the Bot

1. Upload your climbing data file (CSV or JSON)
2. Click "Load & Process Data"
3. Click "Initialize Bot"
4. Ask questions like:
   - "What are my top rated routes?"
   - "How many 5.13a climbs have I done?"
   - "Which area have I climbed in the most?"
   - "What's my hardest climb?"

## File Structure

```
beta-bot/
├── app.py                      # Streamlit web UI
├── ingest.py                   # Data processing pipeline
├── fetch.py                    # Data loading utilities
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── data/
│   └── sample_climbing_data.csv # Example data file
└── cache/                      # Processed data (auto-created)
```

## Architecture

```
Your Climbing Data (CSV/JSON)
         ↓
    fetch.py (load)
         ↓
  ingest.py (process & analyze)
         ↓
   LangChain RAG Pipeline
         ↓
   Ollama Llama2 (local)
         ↓
  Streamlit Web UI
```

## Data Preparation

### From Mountain Project Website

1. Log into Mountain Project
2. Go to your profile → Account Settings
3. Export your climbing history as CSV or JSON
4. Save to `data/` folder

### Alternative: Manual Entry

Create a CSV file with your climbing data and place it in the `data/` folder.

## Troubleshooting

### "Cannot connect to Ollama"
- Make sure `ollama serve` is running in a terminal
- Check that Ollama is installed: `ollama --version`

### "Model 'llama2' not found"
- Pull the model: `ollama pull llama2`
- Check available models: `ollama list`

### Slow responses
- First response is slower (model loading)
- Subsequent responses should be faster
- If very slow, you may have insufficient RAM or storage

### Data format errors
- Make sure CSV has a header row
- JSON must be array of objects
- Required fields: route_name, grade, area, date, rating, type, notes

## Customization

### Use Different LLM

Edit `app.py` line in `init_llm()`:
```python
llm = Ollama(model="mistral", base_url="http://localhost:11434")
```

Available models: `ollama pull mistral`, `ollama pull neural-chat`, etc.

### Adjust Prompt

Edit the `PromptTemplate` in `create_qa_chain()` function in `app.py` to customize bot behavior.

## Tech Stack

- **Backend**: Python 3.8+, LangChain, Ollama
- **Frontend**: Streamlit
- **LLM**: Llama2 (local)
- **Data Processing**: Pandas, JSON

## License

MIT

## Notes

- All data stays on your local machine (no cloud uploads)
- First run takes longer as Llama2 loads into memory
- Requires ~8GB RAM minimum for Llama2
- Responses are faster on subsequent queries due to caching
