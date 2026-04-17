# Curalink - AI Medical Research Assistant (MERN + Open Source LLM)

Full-stack prototype for research-backed medical assistant behavior:
- Structured + natural query input
- Deep retrieval from OpenAlex, PubMed, and ClinicalTrials.gov
- Re-ranking pipeline for precision
- Multi-turn context memory in MongoDB
- Open-source LLM reasoning via local Ollama (through Python FastAPI service)

## 1) Project Structure

- `backend/` - Express + MongoDB API + retrieval/ranking orchestration
- `frontend/` - React + Vite cinematic UI/chat experience
- `llm-service/` - FastAPI service that calls Ollama model for grounded response synthesis

## 2) Setup

## Prerequisites
- Node.js 20+
- Python 3.11+
- MongoDB running locally (or cloud URI)
- Ollama installed locally

### Pull an open model in Ollama
```bash
ollama pull llama3.1:8b
```

## 3) Environment Files

### Backend
Copy `backend/.env.example` to `backend/.env`.

### Frontend
Copy `frontend/.env.example` to `frontend/.env`.

### LLM service
Copy `llm-service/.env.example` to `llm-service/.env`.

## 4) Run Locally

Open 3 terminals:

### Terminal A - LLM service (Python virtual env already created)
```bash
cd llm-service
.\.venv\Scripts\activate
uvicorn app:app --reload --port 8000
```

### Terminal B - Backend
```bash
cd backend
npm run dev
```

### Terminal C - Frontend
```bash
cd frontend
npm run dev
```

Frontend opens at `http://localhost:5173`.

## 5) End-to-End Pipeline

1. User enters disease/context + question.
2. Backend expands query (`intent + disease`) and generates alternatives.
3. Retrieves a large candidate set:
   - OpenAlex: up to 120
   - PubMed: up to 120
   - ClinicalTrials.gov: up to 100
4. Ranks by:
   - lexical relevance
   - recency
   - source credibility
   - location/recruitment boosts for trials
5. Top publications/trials are sent to custom LLM service.
6. LLM synthesizes structured response with citations.
7. Conversation state persists in MongoDB for follow-ups.

## 6) Example Queries

- Latest treatment for lung cancer
- Clinical trials for diabetes
- Top researchers in Alzheimer's disease
- Recent studies on heart disease

## 7) Deployment Notes

- Frontend: deploy on Vercel/Netlify
- Backend: deploy on Render/Railway
- LLM service:
  - local demo with Ollama (fastest for hackathon demo), or
  - host on VM with Ollama installed
- MongoDB: Atlas

For hackathon submission, include:
- Live URL (frontend + connected backend)
- Loom video showing architecture, retrieval pipeline, ranking, and real live query demo.
