# AI POC — Multi-Agent Desk (Atlas)

ChatGPT-style app. **Atlas** (LangGraph supervisor) routes each turn to **sdr**, **sales**, **quote**, or **chat**. Data lives in MongoDB; progress streams over SSE.

**Architecture (diagrams, state, LLM context, multi-execution HITL):** see [`ARCHITECTURE.md`](./ARCHITECTURE.md) — especially **§5 Sales multi-execution HITL**.

## Agents

| Agent | Role |
| --- | --- |
| **Atlas** (supervisor) | Routes the turn |
| **SDR** | Company / customer discovery (ReAct tool loop) |
| **Sales** | Import / delete users with Approve / Reject (HITL) |
| **Quote** | Create / list quotes |
| **Chat** | Simple CRM lookup / small talk |

### Sales human-in-the-loop

After SDR shows customers:

```
Import this
```

Atlas routes to **Sales**, parks a waiting **execution**, and shows **Approve / Reject**.
You can keep chatting (SDR / Quote); Approve later still works via `execution_id`.
Approve writes Customers (Today / Yesterday / Older).

```
Delete the users I added today
Delete user Ajai
```

### SDR tools

| Tool | Purpose |
| --- | --- |
| `search_companies` | Region / HS / products / role / keywords |
| `get_company_details` | Full profile by `companyId` |
| `search_customers` | Contacts for the locked company |

Code: `backend/app/agents/sdr/`

### Seed Atlas data

```bash
cd backend && source .venv/bin/activate
python -m scripts.seed_atlas_data
```

Loads 20 companies + 47 customers from `app/data/atlas_dummy_data.json`.

### Try SDR

```
Find buyers in India for motorcycles with high shipping volume
```

Then pick a company (e.g. `CMP001`) and:

```
Show customers for this company
```

## Customer fields (CRM users)

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | |
| `email` | yes | unique |
| `age` | no | integer |
| `contact_number` | no | string (keeps leading zeros) |
| `is_active` | no | defaults to `true` |

## Quote fields

| Field | Required | Notes |
| --- | --- | --- |
| Customer | yes | email **or** user id (must already exist) |
| `origin` | yes | e.g. Shanghai |
| `destination` | yes | e.g. Rotterdam |
| `mode` | yes | e.g. FCL, LCL |
| `cargo` | yes | e.g. FAK |
| `cut_off_date` | yes | e.g. 25th June |
| `quote_number` | auto | `QTE00000001` |
| `status` | auto | `PENDING` |

## Prerequisites

- Python 3.11+
- Node 18+
- Docker (for local Mongo) or a local `mongod`
- A [Groq API key](https://console.groq.com/keys) (default) or [Gemini API key](https://aistudio.google.com/apikey)

## Setup

```bash
cp .env.example backend/.env
# set ACTIVE_PROVIDER=groq and GROQ_API_KEY (or gemini + GEMINI_API_KEY)
# ACTIVE_MODEL selects the model for the active provider

# skip this if mongod is already running on 27017
docker compose up -d

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed_atlas_data
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Open http://localhost:5173

## Try it

**Atlas / SDR**

```
Find buyers in India for motorcycles
```

**Import customers (Sales HITL)**

```
Import this
```

**Create a CRM user**

```
Create the user name:Ajai, age 34, email ajai@test.com, contact number 9876543210
```

**Create a quote** (customer must exist)

```
Create a quote for ajai@test.com Origin: Shanghai Destination: Rotterdam Mode: FCL Cargo: FAK Cut Off Date: 25th June
```

**List quotes for a customer**

```
Get all quotes for ajai@test.com
```

Open **Users** and **Quotes** in the nav to see CRM Mongo records. Discovery is on the **Atlas** chat page.
