# MIT Hackathon — **UNMAPPED**

Monorepo: **Lovable / TanStack frontend** + **Python FastAPI backend** for the World Bank Youth Summit hack (skills → ESCO/ISCO, LMIC risk, ILO/World Bank/Wittgenstein signals, optional Tavily live opportunities).

Original frontend layout from [myousaf179/MIT_Hackaton](https://github.com/myousaf179/MIT_Hackaton) (`frontend/`).

## Quick start (local)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Add UNMAPPED_TAVILY_API_KEY to .env for live opportunity/news (optional)
python -m scripts.seed_demo
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env.local`. If `VITE_API_URL` is empty, the UI uses the built-in **mock** API.

## Tests

```bash
cd backend && python -m pytest -q
cd frontend && npm run lint && npm run build
```

## Layout

| Path         | Description                                      |
| ------------ | ------------------------------------------------ |
| `frontend/`  | Vite + React 19, calls `POST /analyze` when configured |
| `backend/`   | FastAPI app (`uvicorn api.app:app`)              |

## Security

- Do **not** commit `backend/.env` or `frontend/.env.local`.
- Rotate any API key that was shared in issues or chat.

## License

See individual packages; default MIT for backend as in the original unmapped project.
