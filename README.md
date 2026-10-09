# Travel Policy Bot

A Streamlit chat assistant for answering employee questions about company travel policies for air, rail, and bus trips. It retrieves passages from local policy documents and can use Gemini to write concise answers grounded in those passages.

> **Information only:** The assistant does not book, cancel, reschedule, or modify travel and has no connection to live ticketing systems or availability.

## What it can answer

The intended topics are booking procedures, cancellations, refunds, rescheduling, fare or ticket conditions, baggage, approved providers, and travel guidance for air, rail, and bus. It answers only from the selected mode's policy documents. Where no clearly relevant passage is found, it says that the selected database does not cover the question. It must not invent policy deadlines, eligibility, amounts, or approved operators.

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

The app opens in a browser. Choose Airways, Bus, or Train. Airways requires choosing SpiceJet, IndiGo, or Air India; Bus requires choosing redBus, AbhiBus, MakeMyTrip, or APSRTC Official Portal. Provider queries search only that provider's nested folder, never another carrier/platform's passages or the generic mode library. Train questions use the railways policy folder. Changing transport mode or provider starts a fresh conversation. The four common questions use concise provider-specific answer records with linked sources. Other questions are answered only when the selected provider's database has relevant information; unsupported questions are declined instead of answered from general knowledge. Choose Light or Dark from the app menu under **Settings → Theme**. The included knowledge base is general starter guidance, not an official company policy manual. Verify provider rules and replace or supplement it with approved company policy before using it operationally.

Put train files in `data/sample_policies/railways/`. Airline files belong under `data/sample_policies/airways/<airline>/` (`spicejet`, `indigo`, `air_india`). Bus platform/operator files belong under `data/sample_policies/bus/<provider>/` (`redbus`, `abhibus`, `makemytrip`, `apsrtc`). The folder determines provider scope for retrieval. See [policy-content-notes.md](docs/policy-content-notes.md) before adding or changing policy material. Cross-mode background references live in `docs/policy-reference/` and are kept outside the searchable policy corpus.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Empty | Optional API key for concise answers grounded in retrieved excerpts |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model identifier |
| `POLICY_DIR` | `data/sample_policies` | Root directory containing `airways`, `railways`, and `bus` subfolders |
| `POLICY_TOP_K` | `5` | Maximum matching passages supplied to an answer |

Keep `.env` and API credentials private. Restart the Streamlit app after changing environment settings or policy files; the document index is cached for the app session.

## How it works

1. `src/document_processor.py` reads documents from policy folders, preserves headings, and tags provider subfolders as metadata.
2. `src/policy_retriever.py` normalizes common question wording and ranks passages only within the selected mode and selected airline/platform when applicable.
3. `src/chatbot.py` validates questions, requires a mode and provider when applicable, declines unsupported questions, and returns reviewed provider-specific answers for the four common topics.
4. `src/gemini_client.py` calls the Gemini `generateContent` REST endpoint when configured. If generation fails, matching passages remain available as a fallback.
5. `app.py` provides the Streamlit interface and displays source filenames.

Retrieval is lexical, not semantic. Scanned PDFs without a text layer are not OCR processed. A matching topic is not a guarantee that every ticket-specific detail is present: check the cited policy and ticket terms before acting. If Gemini is configured, it receives only selected-mode excerpts; otherwise the app assembles a short answer from relevant complete passages. Unsupported questions are declined.

## Project layout

```text
app.py                  Streamlit application
config.py               Environment-based settings
requirements.txt        Runtime dependencies
requirements-dev.txt    Development dependencies
.env.example            Safe environment-variable template
.streamlit/config.toml  Streamlit theme
src/                    Document loading, retrieval, safeguards, and Gemini client
data/sample_policies/   Mode-specific policy knowledge files
docs/                   Policy maintenance notes and cross-mode references
tests/                  Test file placeholders
```

The current files under `tests/` are empty placeholders, so automated test coverage has not been implemented yet. Install development dependencies with `pip install -r requirements-dev.txt` when adding tests. `.env` and `.venv/` are local setup files and are excluded from version control.

For actual bookings, cancellations, or changes, use the company travel portal or contact the travel desk.
