# Backend (FastAPI)

## Run the API locally

Use the project **virtualenv** so `uvicorn` is found (macOS `python3` from Command Line Tools often has **no** `uvicorn` → `No module named uvicorn`).

**Option A — activate venv**

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Option B — venv without activating**

```bash
cd backend
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If `venv` does not exist yet: `python3 -m venv venv` (from `backend/`), then install and run as above.

Health check: `http://127.0.0.1:8000/api/health`

## Exit code 143 / Cursor “task failed”

If a background task or IDE reports **failure with exit code 143**, that is usually **not an application crash**.

- **143 = 128 + 15** → the process received **SIGTERM** (polite shutdown).
- Typical causes: you pressed **Ctrl+C**, ran **`kill <pid>`**, stopped servers from another step, or the IDE/session ended the wrapped process.
- Uvicorn logs like `Shutting down` / `Finished server process` mean shutdown was **normal**.

Only investigate as a bug if the log shows a **traceback** or **exit before** “Application startup complete”.
