# GFC Financial AI Chatbot

A lightweight RAG (Retrieval-Augmented Generation) chatbot that answers natural language questions about Apple, Microsoft, and Tesla 10-K filings (FY2023–FY2025).

Built as a BCG Junior Data Scientist engagement deliverable for Global Finance Corp (GFC).

---

## What it does

- Answers complex financial questions grounded strictly in 10-K data — no hallucinations, no outside knowledge
- Maintains conversation history for context-aware follow-up questions
- Retrieves only the relevant data chunks per question rather than dumping everything into the prompt
- Serves a clean chat UI directly from the FastAPI backend

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini (`gemini-3.5-flash-lite`) via `google-genai` |
| Backend | FastAPI + Uvicorn |
| RAG | Custom keyword-based retriever (no vector DB required) |
| Data | Pandas — reads from CSV exports of the 10-K Excel workbook |
| Frontend | Plain HTML / CSS / Vanilla JS (no framework, no build step) |

---

## Project structure

```
GFC_10K_ANALYSIS/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app — routes, CORS, startup, static file serving
│   ├── rag.py           # build_chunks(), retrieve(), ask_chatbot()
│   └── data_loader.py   # loads raw_data.csv and ratios.csv into DataFrames
│
├── frontend/
│   └── index.html       # Self-contained chat UI (HTML + CSS + JS)
│
├── Chat Bot/
│   ├── chat_bot.ipynb   # Original rule-based chatbot (predefined queries)
│   └── testing_AI.ipynb # Gemini API testing + RAG prototyping notebook
│
├── charts/              # Pre-generated trend charts (PNG)
├── raw_data.csv         # Exported from GFC_10K_Financial_Analysis.xlsx
├── ratios.csv           # Exported from GFC_10K_Financial_Analysis.xlsx
├── export_csv.py        # One-time script to export Excel sheets to CSV
├── analysis.ipynb       # Financial analysis notebook
├── Report_deliverable.md # Full written analysis report
├── requirements.txt
└── .env                 # API keys (not committed — see setup below)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/GFC_10K_ANALYSIS.git
cd GFC_10K_ANALYSIS
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_google_api_key_here
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 5. Prepare the data

If you have the original Excel workbook, run:

```bash
python export_csv.py
```

This exports `raw_data.csv` and `ratios.csv` to the project root. If the CSVs are already present, skip this step.

### 6. Start the server

```bash
venv\Scripts\uvicorn.exe app.main:app --reload
```

Open your browser at `http://127.0.0.1:8000`.

---

## Usage

### Chat UI

Navigate to `http://127.0.0.1:8000` — the chat interface loads directly.

Use the suggestion chips to get started, or type any financial question:

- *"Which company had the highest net margin in FY2025?"*
- *"How has Tesla's profitability changed over the years?"*
- *"Compare Microsoft and Apple's revenue growth."*
- *"Why is Apple's ROE so much higher than Microsoft's?"*

The bot maintains conversation history within the session — you can ask follow-up questions naturally.

### API

The backend exposes two endpoints:

#### `GET /health`
Returns server status and number of loaded chunks.

```json
{ "status": "ok", "chunks_loaded": 22 }
```

#### `POST /ask`
Ask a financial question with optional conversation history.

**Request:**
```json
{
  "question": "Which company had the best margins?",
  "history": [
    { "role": "user", "text": "Tell me about Tesla's revenue growth." },
    { "role": "bot",  "text": "Tesla's revenue growth reversed from +18.8% in FY2023 to -2.9% in FY2025..." }
  ]
}
```

**Response:**
```json
{
  "answer": "Microsoft had the highest net margin in FY2025 at 36.1%..."
}
```

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

---

## How the RAG system works

1. **Chunking** — on startup, financial data is converted into 22 labeled text chunks: one per company per year for raw financials, one per company per year for ratios, and four narrative analysis chunks (one per company + one cross-company comparison).

2. **Retrieval** — each incoming question is scored against all chunks using keyword overlap across company names, fiscal years, and financial topics. The top 5 most relevant chunks are selected.

3. **Generation** — the retrieved chunks plus any conversation history are injected into a structured prompt. Gemini answers using only the provided data — it is explicitly instructed not to use outside knowledge.

---

## Data coverage

| Company | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Apple | ✓ | ✓ | ✓ |
| Microsoft | ✓ | ✓ | ✓ |
| Tesla | ✓ | ✓ | ✓ |

Metrics: Revenue, Gross Profit, Operating Income, Net Income, Total Assets, Total Equity, Operating Cash Flow, CapEx, Gross Margin, Operating Margin, Net Margin, ROE, ROA, Current Ratio, Debt-to-Equity, Free Cash Flow, Revenue Growth YoY.

Source: SEC EDGAR 10-K annual filings.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |

---

## .gitignore

Make sure your `.gitignore` includes:

```
.env
venv/
__pycache__/
*.pyc
*.pyo
.ipynb_checkpoints/
```

---

## License

MIT
