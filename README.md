# Travel Policy Bot

A Streamlit chat assistant for answering employee questions about company travel policies for air, rail, and bus trips. It retrieves passages from local policy documents and can use Gemini to write concise answers grounded in those passages.

> **Information only:** The assistant does not book, cancel, reschedule, or modify travel and has no connection to live ticketing systems or availability.

## What it can answer

The intended topics are booking procedures, cancellations, refunds, rescheduling, fare or ticket conditions, baggage, approved providers, and travel guidance for air, rail, and bus. It answers only from the policy documents supplied to it. Where no relevant passage is found, it says so and directs employees to the travel portal or travel desk. It must not invent policy deadlines, eligibility, amounts, or approved operators.

## Requirements

- Python 3.10 or newer
- Policy documents in `.txt`, `.md`, or text-based `.pdf` format
- Optional Gemini API key for generated answers; local excerpt retrieval works without it

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add mode-specific policy documents under data/sample_policies/airways, /railways, or /bus
# Optionally set GEMINI_API_KEY in .env
streamlit run app.py
```

The app opens in a browser. Choose Airways, Railways, or Bus, enter a question, and review the cited source filenames. Retrieval is restricted to the selected mode. With Gemini configured, answers are requested as a few short bullet points. Without a Gemini key, the app selects matching complete sentences from policy passages and formats them as concise points. The included mode-specific knowledge base is general starter guidance, not an official company policy manual. Verify provider rules and replace or supplement it with approved company policy before using it operationally.

Put mode-specific files in the matching folder: `data/sample_policies/airways/`, `data/sample_policies/railways/`, or `data/sample_policies/bus/`. The corresponding mode folder determines which mode can retrieve a document. Documents outside those folders are not used for mode-specific answers. See [policy-content-notes.md](docs/policy-content-notes.md) before adding or changing policy material. Cross-mode background references live in `docs/policy-reference/` and are kept outside the searchable policy corpus.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Empty | Optional API key; when unset, answers show retrieved excerpts |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model identifier |
| `POLICY_DIR` | `data/sample_policies` | Root directory containing `airways`, `railways`, and `bus` subfolders |
| `POLICY_TOP_K` | `5` | Maximum matching passages supplied to an answer |

Keep `.env` and API credentials private. Restart the Streamlit app after changing environment settings or policy files; the document index is cached for the app session.

## How it works

1. `src/document_processor.py` reads documents from the selected mode folder, preserves headings, and splits long sections into overlapping passages.
2. `src/policy_retriever.py` normalizes common question wording (such as “documentation” and “documents”) and ranks passages using topic and filename matches within the selected mode.
3. `src/chatbot.py` validates questions, declines transaction requests, and orchestrates retrieval and response generation.
4. `src/gemini_client.py` calls the Gemini `generateContent` REST endpoint when configured. If generation fails, matching passages remain available as a fallback.
5. `app.py` provides the Streamlit interface and displays source filenames.

Retrieval is lexical, not semantic. Scanned PDFs without a text layer are not OCR processed. Gemini responses depend on the supplied documents and should be checked against the cited policy before acting.

## Project layout

```text
app.py                  Streamlit application
config.py               Environment-based settings
src/                    Document loading, retrieval, safeguards, and Gemini client
data/sample_policies/   Mode-specific starter knowledge base and approved policy files
docs/                   Policy maintenance notes and cross-mode reference material
```

For actual bookings, cancellations, or changes, use the company travel portal or contact the travel desk.
