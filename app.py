"""
Streamlit web UI for Mountain Project Q&A Bot.
Uses LangChain with Ollama (Llama2) model for RAG.
"""

import os
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

from langchain_ollama import OllamaLLM

from ingest import ClimbingDataProcessor
from fetch import load_climbing_data


# Page configuration
st.set_page_config(
    page_title="Mountain Project Q&A Bot",
    page_icon="🧗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.llm = None
    st.session_state.context = ""
    st.session_state.messages = []


def init_llm(api_key: str = None):
    """Initialize Ollama Llama2 LLM connection."""
    try:
        # Note: api_key parameter kept for compatibility but not used with Ollama
        llm = OllamaLLM(
            model="llama2",
            base_url="http://localhost:11434",
            temperature=0.2,
        )
        # Test connection
        _ = llm.invoke("Hello")
        return llm
    except Exception as e:
        st.error(f"❌ Cannot connect to Ollama. Make sure Ollama is running on http://localhost:11434\nError: {e}")
        return None


def load_and_process_data(data_path: str):
    """Load and process climbing data."""
    try:
        raw_data = load_climbing_data(data_path)
        processor = ClimbingDataProcessor(raw_data)
        result = processor.process()
        return result, processor.get_context_for_llm()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None, None


def create_prompt(context: str, chat_history: str, question: str) -> str:
    """Create a prompt string for Ollama Llama2."""
    return f"""You are a helpful assistant that answers questions about climbing data.

Climbing History Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer: Based on the climbing data and context provided, here's what I found:"""


# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    
    data_file = st.file_uploader(
        "📁 Upload climbing data (CSV or JSON)",
        type=["csv", "json"],
        help="CSV or JSON file with your climbing history"
    )
    
    if data_file is not None:
        # Save uploaded file temporarily
        data_path = f"data/{data_file.name}"
        Path("data").mkdir(exist_ok=True)
        with open(data_path, "wb") as f:
            f.write(data_file.getbuffer())
        
        if st.button("🔄 Load & Process Data"):
            with st.spinner("Processing data..."):
                result, context = load_and_process_data(data_path)
                if result:
                    st.session_state.context = context
                    st.session_state.data = result
                    st.success(f"✅ Loaded {result['processed_count']} climbs!")
    
    st.divider()
    
    if st.button("🚀 Initialize Bot", key="init_button"):
        with st.spinner("Connecting to Ollama (Llama2)..."):
            llm = init_llm()
            if llm and st.session_state.context:
                st.session_state.llm = llm
                st.session_state.initialized = True
                st.success("✅ Bot ready!")
            elif not st.session_state.context:
                st.error("⚠️ Please load data first")
    
    st.divider()
    
    st.markdown("### 📖 Help")
    st.markdown("""
- **Upload Data**: Select your Mountain Project CSV or JSON export
- **Initialize Bot**: Start the chatbot (requires Ollama running on http://localhost:11434)
- **Ask Questions**: Query your climbing history naturally

### 🔧 Setup
Make sure Ollama is running:
```
ollama serve llama2
```
    """)


# Main content
st.title("🧗 Mountain Project Q&A Bot")
st.markdown("Ask questions about your climbing history!")

if st.session_state.data and "statistics" in st.session_state.data:
    # Display statistics
    stats = st.session_state.data["statistics"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Climbs", stats.get("total_climbs", 0))
    with col2:
        st.metric("Unique Routes", stats.get("unique_routes", 0))
    with col3:
        st.metric("Areas Visited", stats.get("unique_areas", 0))
    with col4:
        st.metric("Avg Rating", f"{stats.get('average_rating', 0):.1f}")
    
    st.divider()

# Chat interface
st.subheader("💬 Ask Your Questions")

if not st.session_state.initialized:
    st.warning("⚠️ Please upload data and initialize the bot in the sidebar to get started.")
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    if user_input := st.chat_input("Ask me about your climbs..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Build chat history string
                    chat_history = "\n".join([
                        f"{msg['role'].capitalize()}: {msg['content']}"
                        for msg in st.session_state.messages[:-1]
                    ])
                    
                    # Generate prompt and get response from Ollama
                    prompt = create_prompt(
                        context=st.session_state.context,
                        chat_history=chat_history,
                        question=user_input,
                    )
                    response = st.session_state.llm.invoke(prompt)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    st.error(f"❌ Error generating response: {e}")

# Footer
st.divider()
st.markdown("""
**Example Questions:**
- What are my top rated routes?
- How many 5.13a climbs have I done?
- Which area have I climbed in the most?
- What's my hardest climb?
- How many different types of routes have I tried?
""")