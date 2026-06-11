# Mountain Project Q&A Bot - Setup Guide

## Your Data Summary

✅ **396 climbs processed successfully!**

- **Unique Routes:** 396
- **Unique Areas:** 41
- **Unique Grades:** 41
- **Primary Locations:** Red River Gorge (KY), New River Gorge (WV)
- **Top Areas:** Miller Fork, Muir Valley, Sore Heel Hollow, Northern Gorge, Bald Rock
- **Grade Distribution:** Mostly 5.12a/b/c and 5.11c/d sport climbing
- **Average Rating:** 3.0/5.0

---

## Setup Instructions

### Step 1: Install Ollama (One-Time Setup)

1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Install and restart your computer
3. Open **PowerShell** and verify:
   ```powershell
   ollama --version
   ```

### Step 2: Download Llama2 Model

In PowerShell:
```powershell
ollama pull llama2
```

**⏱️ This takes 5-10 minutes** and downloads ~3.8 GB.

Verify with:
```powershell
ollama list
```

You should see `llama2` in the list.

---

## Running the Bot

You'll need **two separate terminal windows** running simultaneously.

### Terminal 1: Start Ollama Server

```powershell
ollama serve
```

**✅ Keep this running!** You should see:
```
listening on 127.0.0.1:11434
```

### Terminal 2: Start Streamlit App

Navigate to your project folder:
```powershell
cd c:\Users\NC740\repos\beta-bot
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Your browser will automatically open at `http://localhost:8501`

---

## Using the Bot

### Interface Overview

**Left Sidebar:**
- Shows data statistics from your 396 climbs
- Click "Initialize Bot" to connect to Ollama
- See system status and example questions

**Main Chat Area:**
- Upload your `ticks.csv` file (pre-loaded if you used the sample)
- Chat with the bot about your climbing history

### Example Questions to Try

```
"What are my top rated routes?"
"How many 5.13a climbs have I done?"
"Which area have I climbed in the most?"
"What's my hardest climb?"
"How many different types of routes have I tried?"
"What grade do I climb most often?"
"Tell me about my climbing in Red River Gorge"
"How many Sport routes vs Trad routes have I climbed?"
```

---

## Troubleshooting

### Problem: "Cannot connect to Ollama"

**Solution:** Make sure Terminal 1 is running `ollama serve`

Check connection manually:
```powershell
curl http://localhost:11434/api/tags
```

### Problem: "Model 'llama2' not found"

**Solution:** Run `ollama pull llama2` again

### Problem: Very slow responses

**Solutions:**
- First response takes longer (model loading) - normal
- Check your computer has 8+ GB RAM
- Close other applications
- Check your storage has 10+ GB free space

### Problem: App won't load

**Solutions:**
- Activate the virtual environment: `.\venv\Scripts\Activate.ps1`
- Check Python: `python --version`
- Reinstall requirements: `pip install -r requirements.txt`

### Problem: "streamlit not found"

**Solution:** Activate the virtual environment first:
```powershell
.\venv\Scripts\Activate.ps1
```

---

## Advanced Usage

### Update with New Data

1. Export fresh data from Mountain Project
2. Save to `data/` folder
3. Upload via the web interface
4. Click "Load & Process Data"
5. Chat about your latest climbs!

### Customize the Bot

Edit the **prompt template** in `app.py` (~line 70) to change bot personality:

```python
template="""You are a helpful assistant that answers questions about climbing data.

Climbing History Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer: Based on the climbing data and context provided, here's what I found:"""
```

### Use Different LLM

Edit `init_llm()` in `app.py`:

```python
# Change from:
llm = Ollama(model="llama2", base_url="http://localhost:11434")

# To other models:
llm = Ollama(model="mistral", base_url="http://localhost:11434")
```

Then pull the model:
```powershell
ollama pull mistral
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `ollama serve` | Start local LLM server |
| `ollama pull llama2` | Download Llama2 model |
| `ollama list` | Show installed models |
| `streamlit run app.py` | Start web UI |
| `python ingest.py data/ticks.csv` | Process climbing data |

---

## File Structure

```
beta-bot/
├── app.py                          # Streamlit web UI
├── ingest.py                       # Data processing
├── fetch.py                        # Data loading
├── requirements.txt                # Dependencies
├── SETUP.md                        # This file
├── data/
│   ├── ticks.csv                  # Your climbing data (396 climbs)
│   └── sample_climbing_data.csv   # Example format
└── cache/
    └── processed_data.json        # Processed data
```

---

## System Requirements

- **RAM:** 8+ GB (for Llama2)
- **Storage:** 10+ GB (for model)
- **Internet:** For downloading models (one-time)
- **Python:** 3.8+
- **OS:** Windows, macOS, Linux

---

## What's Happening Behind the Scenes

```
Your Climbing Data (396 ticks)
         ↓
   Ingested & Analyzed
   (grades, areas, stats)
         ↓
   Formatted as Context
         ↓
   Your Question
         ↓
   LangChain RAG Pipeline
   (injects context)
         ↓
   Ollama Llama2 (Local)
         ↓
   Intelligent Answer
   (based on YOUR data)
```

---

## All Data Stays Local

✅ **Privacy:** Your data NEVER leaves your computer  
✅ **Offline:** Works without internet after setup  
✅ **Free:** No API fees or subscriptions  
✅ **Open Source:** Llama2 is fully open source  

---

**Enjoy your climbing Q&A bot! 🧗**
