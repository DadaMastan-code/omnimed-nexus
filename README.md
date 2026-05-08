# OmniMed-Nexus

> **God-mode ML orchestration hub** — connects [codesense-ai](https://github.com/DadaMastan-code/codesense-ai), [MedFusion-Leuk](https://github.com/DadaMastan-code/MedFusion-Leuk), and [medbrain-ai](https://github.com/DadaMastan-code/medbrain-ai) into one self-improving system.

---

## Architecture

```
  GitHub Webhooks (all 3 repos)
           │
           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                  OmniMed-Nexus Hub                      │
  │                                                         │
  │  Webhook Server ──► LangGraph Meta-Agent                │
  │                           │                             │
  │          ┌────────────────┼────────────────┐            │
  │          ▼                ▼                ▼            │
  │   codesense-ai     MedFusion-Leuk     medbrain-ai       │
  │   (code review)    (diagnosis)        (clinical reason) │
  │          │                │                │            │
  │          └────────────────┴────────────────┘            │
  │                           │                             │
  │              Qdrant · Neo4j · MLflow                    │
  └─────────────────────────────────────────────────────────┘
           │
           ▼
  Next.js Dashboard (port 3000)
```

## What this does

| Feature | Description |
|---|---|
| **Auto PR Review** | Every PR across all 3 repos is reviewed by codesense-ai and posted as a comment |
| **Model Sync** | When MedFusion-Leuk ships a new checkpoint, medbrain-ai is automatically notified |
| **Issue Analysis** | GitHub Issues tagged `omnimed-nexus` are autonomously analysed by the meta-agent |
| **Unified RAG** | All three repos' code and docs are indexed in one Qdrant knowledge base |
| **Knowledge Graph** | Cross-repo relationships tracked in Neo4j |
| **Model Registry** | Unified MLflow registry for all models — one place to compare, promote, deploy |
| **Self-Review** | Daily scheduled workflow: codesense-ai reviews all three repos and files issues |
| **Dashboard** | Live view of repo health, findings, and model status |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/DadaMastan-code/omnimed-nexus
cd omnimed-nexus

# 2. Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_APP_ID, etc.

# 3. Boot infrastructure
docker compose up -d qdrant neo4j postgres mlflow

# 4. Install Python deps
pip install uv && uv pip install --system -e .

# 5. Start webhook server
uvicorn github_app.main:app --reload --port 8000

# 6. Index all repos into Qdrant
python -c "import asyncio; from rag_layer.indexer import index_all_repos; asyncio.run(index_all_repos())"

# 7. Start dashboard
cd dashboard && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the dashboard.

## GitHub App Setup

1. Create a GitHub App at [github.com/settings/apps/new](https://github.com/settings/apps/new)
2. Set webhook URL to `https://your-server/webhook`
3. Subscribe to: `Pull requests`, `Pushes`, `Issues`
4. Install the app on all three repos
5. Download the private key and save as `github-app.pem`
6. Fill `GITHUB_APP_ID` and `GITHUB_WEBHOOK_SECRET` in `.env`

## GitHub Secrets Required

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OMNIMED_GITHUB_TOKEN` | PAT with `repo` scope on all 3 repos |
| `CODESENSE_API_URL` | codesense-ai API endpoint |
| `MEDFUSION_API_URL` | MedFusion-Leuk API endpoint |
| `MEDBRAIN_API_URL` | medbrain-ai API endpoint |
| `MLFLOW_TRACKING_URI` | MLflow server URL |
| `NEO4J_URI` | Neo4j bolt URI |
| `NEO4J_PASSWORD` | Neo4j password |
| `QDRANT_HOST` | Qdrant host |
| `QDRANT_API_KEY` | Qdrant API key (Qdrant Cloud) |

## Self-Improvement Loop

```
Daily at 02:00 UTC:
  codesense-ai reviews all 3 repos
       │
       ▼
  Issues filed for problems found
       │
       ▼
  Meta-agent analyses issues
       │
       ▼
  Fix PRs proposed
       │
       ▼
  codesense-ai reviews those PRs   ← cycle continues
```

## Stack

- **Orchestration**: LangGraph 0.3+, Claude claude-sonnet-4-6
- **Vector DB**: Qdrant (unified knowledge base)
- **Graph DB**: Neo4j (cross-repo relationships + findings)
- **Model Registry**: MLflow (unified across all models)
- **Webhook Server**: FastAPI
- **Dashboard**: Next.js 15, Tailwind CSS 4, Recharts
- **CI/CD**: GitHub Actions (3 workflows)
- **Infra**: Docker Compose

## License

MIT
