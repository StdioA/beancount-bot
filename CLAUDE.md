# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Beancount Bot is a Python-based IM bot for quickly recording simple Beancount transactions. It supports Telegram, Mattermost, and a web-based PWA frontend. The core parses natural-language-like input into Beancount transactions, with fallback to vector database matching and LLM-based RAG completion.

## Common Commands

### Run the bot
```bash
# Telegram frontend
python main.py telegram -c config.yaml

# Mattermost frontend
python main.py mattermost -c config.yaml

# Web frontend (serves PWA at configured host:port)
python main.py web -c config.yaml
```

### Lint
```bash
make lint              # ruff check
```

### Test
```bash
make test              # Run full suite with coverage (outputs htmlcov/)
pytest path/to/file_test.py  # Run a single test file
```

### Frontend (web UI)
```bash
cd frontend
npm run dev            # Vite dev server
npm run build          # Production build (static files served by web_bot)
npm run watch          # Watch mode build
npm run lint           # ESLint
```

### i18n
```bash
make gentranslations   # Regenerate .po files from source
make compiletranslations  # Compile .po to .mo
```

## Architecture

### Entrypoint and Initialization
`main.py` parses CLI arguments and calls `init_bot(config_path)`, which loads `config.yaml`, sets up gettext i18n, configures logging, and initializes the global `BeanManager`. It then imports and runs the selected bot frontend.

### Core Transaction Logic (`bean_utils/`)
- `bean.py`: `BeanManager` is the central class. It loads the Beancount ledger via `beancount.loader`, auto-reloads when files change, and exposes `generate_trx()` to turn user input into one or more candidate Beancount transactions. It also handles `/expense` and `/bill` queries via BQL (`beanquery`).
- `vec_query.py`: Handles calls to an OpenAI-compatible embedding API and builds/searches the vector database of historical transactions.
- `rag.py`: When vector matching fails, sends the user input plus reference transactions to an LLM to synthesize a complete accounting record.

### Bot Frontends (`bots/`)
`bots/controller.py` contains the shared business logic (`render_txs`, `fetch_expense`, `fetch_bill`, `build_db`, `clone_txs`). Each bot is a thin adapter:
- `telegram_bot.py`: `python-telegram-bot` based, async handlers, owner-only access via chat ID.
- `mattermost_bot.py`: `mmpy-bot` based.
- `web_bot.py`: `bottle` based, serves the built frontend and a REST API for the PWA chat UI.

### Vector Database (`vec_db/`)
Abstracts vector storage. `json_vec_db.py` uses JSON + numpy as a fallback; `sqlite_vec_db.py` uses `sqlite-vec` when available. The `vec_db/__init__.py` selects the backend at runtime based on import availability.

### Configuration and i18n (`conf/`)
- `config_data.py`: Loads and validates `config.yaml`.
- `i18n.py`: gettext wrapper that supports overriding locale via config or environment.

### Frontend (`frontend/`)
Vite + TailwindCSS + TypeScript PWA. Built files are served statically by `web_bot.py`. Communicates with the bottle backend via REST API (`/api/messages`, etc.).

## Configuration

`config.yaml` is required at runtime. See `config.yaml.example` for all options. Key sections:
- `beancount.filename`: Entrypoint ledger file.
- `bot.{telegram,mattermost,web}`: Frontend-specific credentials.
- `embedding`: OpenAI-compatible API for transaction embeddings (optional).
- `rag`: OpenAI-compatible API for LLM fallback (optional).

## Testing Notes

- Tests use pytest and are named `*_test.py`.
- `make test` runs with coverage, omitting bot entrypoints and `main.py`.
- The GitHub Actions workflow in `.github/workflows/unit_test.yml` installs `requirements/full.txt` plus `sqlite-vec` and runs `pytest --cov`.
