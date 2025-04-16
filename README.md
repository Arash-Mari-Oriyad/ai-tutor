# 🧠 AI English Tutor (Proficiency Detector)

This project is an interactive AI Tutor that chats with users in English and automatically detects their CEFR proficiency level (A1–C2) through natural conversation.

It uses:
- **GPT-4o-mini** for language understanding
- **LangGraph** for conversation state management
- **FastAPI** backend
- **Vanilla HTML/JS frontend**
- **Local deployment** (no frontend frameworks required)

---

## 🚀 Features

- Initiates a natural dialogue with users
- Asks a few diagnostic questions
- Assesses user's English level (CEFR A1–C2)
- Displays results directly in a friendly web chat UI
- Fully local setup (only requires OpenAI API key)

---

## 🛠️ Requirements

- Python 3.9+
- Node.js (optional, if you prefer modern frontend)
- OpenAI API key with access to GPT-4o-mini

---

## 📦 Installation

### 1. Clone the project

```bash
git clone https://github.com/Arash-Mari-Oriyad/ai-tutor
cd ai-tutor
```

### 2. Set up Python environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt` yet, create one with:

```txt
fastapi
uvicorn
langgraph
openai
python-dotenv
```

### 4. Add your OpenAI key

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

---

## ▶️ Running the App

### 1. Start the FastAPI server

```bash
uvicorn main:app --reload
```

The backend will run at: [http://localhost:8000](http://localhost:8000)

### 2. Start the frontend

You have two options:

#### Option A: Open `index.html` directly

- Just double-click `index.html` or open in your browser.

#### Option B: Serve it locally

```bash
python -m http.server 8001
```

Then open [http://localhost:8001](http://localhost:8001)

---

## 💬 How It Works

1. On load, the app greets the user.
2. It asks 3 dynamic questions to assess grammar, fluency, and vocabulary.
3. After the 3rd question, it uses GPT-4o-mini to assess the user's CEFR level.
4. The conversation resets automatically for a new assessment.

---

## ✨ Project Structure

```
.
├── main.py             # FastAPI + LangGraph backend
├── index.html          # Frontend UI
├── .env                # API Key config
├── requirements.txt    # Python dependencies
└── README.md           # This file
```