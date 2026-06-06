# Deploy Live Operator Guide

This is the dashboard-side work the automated runbook can't do for you. Each
section maps 1:1 to a `RUNBOOK_6June_agent_task_tracker.md` phase.

The code-side work is already shipped on `main`:

- `feat(llm): provider-agnostic client (Gemini/Groq)` - `dd14371`
- `fix(deploy): bind run.py to 0.0.0.0:$PORT, disable debug` - `1654b3a`
- `feat(ai-route): surface validator_verdict + agent_trace to clients` - `f652aac`

Render auto-deploys these on push.

---

## PHASE-4.2 - Unblock Render (if /health hangs)

The active backend is healthy as of the last automated probe. If `/health` ever
hangs again, the start command on Render is stale. Fix in dashboard:

1. Render -> the service -> **Settings**
2. **Root Directory:** `backend`
3. **Start Command:**
   `gunicorn run:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
4. **Health Check Path:** `/health`
5. Auto-Deploy: `Yes`, Branch: `main`
6. Confirm env vars match the table below (PHASE-A) and **Manual Deploy ->
   Clear build cache & deploy**.

If you would rather start from scratch with `render.yaml` as source of truth:
delete the manual service, then Render -> New -> Blueprint -> pick the repo.
The URL will change; update everywhere it appears.

---

## PHASE-6 - Vercel frontend (one-time)

1. Vercel -> Add New -> Project -> import `Agent-Task-Tracker`.
2. **Root Directory:** `frontend`
3. **Framework:** Vite
4. **Build:** `npm run build`
5. **Output:** `dist`
6. **Environment Variable - set BEFORE first build (Vite inlines at build time):**

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://agent-task-tracker-8avp.onrender.com` (no trailing slash) |

7. Deploy and copy the resulting origin (e.g. `https://task-tracker.cyrussaas.com`
   or `*.vercel.app`).

GATE: deployed site loads, DevTools Network shows API calls hitting the Render
URL (not `localhost:5000` and not `/undefined/...`). If you see
`/undefined/...` the env var name is wrong or the build was triggered before
the variable was set - re-set and **redeploy** (value is compiled in, not
runtime).

---

## PHASE-7 - Close the CORS loop

Render -> the service -> **Environment** -> set `CORS_ORIGINS` to the exact
Vercel origin (scheme + host, no trailing slash). Save -> Render redeploys
in 1-2 min.

```
CORS_ORIGINS=https://<your-vercel-origin>
```

You can list multiple origins comma-separated if you keep both
`*.vercel.app` and a custom domain. No trailing slashes.

GATE: signup from the deployed UI; DevTools Network shows the OPTIONS preflight
returning 204/200 and POST returning 200 with no CORS console error.

---

## PHASE-8 - Keep the free backend warm

Render free sleeps after 15 min idle and cold-starts in 30-60 s. Set up one
of:

- **cron-job.org** -> Create cronjob -> URL
  `https://agent-task-tracker-8avp.onrender.com/health` -> every **10 minutes**
- **UptimeRobot** -> HTTP(s) monitor on `/health` -> every **5 minutes**

GATE: ping history shows consecutive 200s. One free service keeps you well
under Render's ~750 free instance-hours/month.

---

## PHASE-10 - Rotate exposed secrets

Both the prior `JWT_SECRET` and the Gemini API key were exposed in earlier
sessions; treat them as compromised.

```bash
# Generate a fresh 64-char hex JWT secret
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"
```

Steps:

1. Generate a **new** Gemini API key in Google AI Studio.
2. Delete the old key from AI Studio.
3. In Render -> the service -> Environment: set the new `JWT_SECRET` and the
   new `GEMINI_API_KEY`.
4. Render redeploys; existing JWTs are invalidated (users log in again - this
   is expected).

GATE: old key is gone from AI Studio; fresh signup -> login -> profile works
end-to-end with the new secrets.

---

## PHASE-11 - Demo seed (recruiter polish)

Create one demo account directly via the live API so the dashboard isn't empty
on first load:

```bash
BASE=https://agent-task-tracker-8avp.onrender.com

# Demo account
TOKEN=$(curl -sS -X POST $BASE/signup -H 'Content-Type: application/json' \
  -d '{"email":"demo@demo.dev","password":"demo12345","name":"Demo"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

# Three seed tasks across the three persona modes
for T in '{"title":"Summarize daily standup","description":"Summarize: yesterday we shipped the multi-agent refactor; today we are deploying to Render; blockers: none.","type":"Summarization","priority":"high","schedule":"manual"}' \
         '{"title":"Translate welcome message","description":"Translate to French: Welcome to Agent Task Tracker.","type":"Translation","priority":"medium","schedule":"manual"}' \
         '{"title":"Classify support ticket","description":"Classify this support ticket: My invoice is wrong, please refund.","type":"Classification","priority":"low","schedule":"manual"}'; do
  TID=$(curl -sS -X POST $BASE/tasks -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "$T" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["task_id"])')
  curl -sS -X POST $BASE/tasks/$TID/run-ai -H "Authorization: Bearer $TOKEN" >/dev/null
  echo "seeded $TID"
done
```

Add to the README a "Demo login - use freely: `demo@demo.dev` / `demo12345`".

---

## PHASE-A - Render environment reference

| Key | Value |
|-----|-------|
| `MONGO_URI` | `mongodb+srv://<user>:<pw>@<cluster>.mongodb.net/kpi_agent?retryWrites=true&w=majority` |
| `JWT_SECRET` | fresh 64-char hex (PHASE-10) |
| `JWT_EXP_DAYS` | `1` |
| `LLM_PROVIDER` | `gemini` (or `groq`) |
| `GEMINI_API_KEY` | fresh AI Studio key |
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` |
| `GROQ_API_KEY` | only if `LLM_PROVIDER=groq` |
| `GROQ_MODEL_NAME` | `llama-3.3-70b-versatile` |
| `CORS_ORIGINS` | exact Vercel origin, no trailing slash |

`GEMINI_API_ENDPOINT` is **not** set - it is derived from the model name
in code.

---

## PHASE-13 - Resume vs code reconciliation

These are resume edits only the candidate can make - documented here so they
are not forgotten.

| Resume claim today | Status on `main` | Recommended edit |
|---|---|---|
| `Flask REST API (SQLAlchemy, JWT)` | **FALSE** - app uses `flask_pymongo`, not SQLAlchemy | `Flask REST API (PyMongo, JWT)` or `(MongoDB, JWT)` |
| `LangChain, LangGraph, RAG` | LangChain TRUE (per-agent `PromptTemplate`), LangGraph and RAG NOT in repo | `LangChain (multi-agent), Gemini API` |
| `Dockerized` | TRUE - see `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | keep as-is |
| `Multi-agent` | TRUE - `AnalyzerAgent` -> `ExecutorAgent` -> `ValidatorAgent` | keep as-is |
| `Provider-agnostic LLM client (Gemini/Groq, $0)` | TRUE as of `dd14371` | add this bullet if missing |

Do NOT switch the repo to SQLAlchemy to make the resume true; the working
PyMongo code is the source of truth.
