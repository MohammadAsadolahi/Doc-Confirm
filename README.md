<div align="center">

# GenDoc Confirm

### AI-Powered Document Verification & Comprehension Assurance Platform

**Eliminating hallucinations. Enforcing consistency. Ensuring understanding.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

<br/>

*A system that applies multi-layered verification to AI-generated documents — combining atomic fact decomposition, multi-perspective verification, evidence grounding, contradiction detection, and human comprehension testing into a unified confidence index.*

<br/>

[**Architecture**](#-architecture) · [**Pipeline**](#-verification-pipeline) · [**Quick Start**](#-quick-start) · [**Research**](#-research-foundations)

</div>

---

## Author

**Mohammad Asadolahi** — Senior Agentic AI Engineer

- GitHub: [https://github.com/MohammadAsadolahi](https://github.com/MohammadAsadolahi)
- Focus: Agentic AI Architectures In The Wild

---

## The Problem

Large Language Models generate fluent, convincing text — but they **hallucinate**. They fabricate citations, invent statistics, and produce internally contradictory statements that pass casual review. Worse, users often accept AI-generated documents without truly understanding their content, creating a **comprehension gap** that compounds the risk.

GenDoc Confirm addresses all three failure modes through a unified verification pipeline:

| Failure Mode | Detection Method | Research Basis |
|:---|:---|:---|
| **Hallucinated Facts** | Atomic fact decomposition + multi-perspective verification | FActScore, SAFE |
| **Internal Contradictions** | Cross-reference analysis + cross-examination | CoVe |
| **Blind Acceptance** | Multi-level comprehension quiz with trap questions | Human-AI Collaboration |

---

## Architecture

### Technology Stack

<table>
<tr>
<td width="50%">

**Frontend**
- React 18 + TypeScript + Vite 6
- Tailwind CSS
- Framer Motion animations
- React Query data fetching
- Server-Sent Events for real-time streaming

</td>
<td width="50%">

**Backend**
- FastAPI (Python 3.11+)
- LangChain + LangGraph orchestration
- In-memory session store
- OpenAI-compatible LLM provider

</td>
</tr>
</table>

Docker Compose is provided with PostgreSQL 16, Redis 7, and ChromaDB services for future production use, but the current application implementation uses in-memory storage.

---

## Verification Pipeline

GenDoc Confirm implements a **9-node LangGraph pipeline** with multi-perspective verification and selective cross-examination, informed by research in LLM verification.

### Pipeline Stages

```
+----------------------------------------------------------------------------------+
|                           DOCUMENT INGESTION                                     |
|  [1] Document Generation    -- CoT-prompted generation from user specifications  |
|  [2] Fact Decomposition     -- FActScore-inspired atomic claim extraction        |
+----------------------------------------------------------------------------------+
|                         MULTI-LAYER VERIFICATION                                 |
|  [3] Evidence Grounding     -- Batched grounding against user-provided refs      |
|  [4] Execute Verification   -- Multi-perspective verification (1 call per fact)  |
|  [5] Cross-Examination      -- Selective CoVe-lite for low-confidence facts      |
|  [6] Cross-Reference/Revise -- Contradiction detection + document revision       |
+----------------------------------------------------------------------------------+
|                       COMPREHENSION ASSURANCE                                    |
|  [7] Quiz Generation        -- Multi-level questions: recall, analysis, trap,    |
|                                 scenario                                         |
|  [8] Answer Evaluation      -- Rule-based grading of user answers                |
|  [9] Final Report           -- Composite scoring with risk areas &               |
|                                 recommendations                                  |
+----------------------------------------------------------------------------------+
```

### Pipeline Optimizations

The pipeline applies several research-backed optimizations to reduce LLM calls while preserving verification quality:

- **Batched evidence grounding**: N calls reduced to 1 (RAGAS NLIStatementPrompt pattern)
- **Unified multi-perspective verification**: 3 perspectives in 1 call per fact (Self-Contrast, SPP research)
- **Selective cross-examination**: Only facts with confidence < 0.6 are cross-examined (CoVe Factored Lite)
- **Merged cross-reference + revision**: Single step combining contradiction detection and document correction

---

## Composite Confidence Index

The final Confidence Index is a weighted composite of four independently measured dimensions:

$$CI = 0.35 \cdot F_{factuality} + 0.25 \cdot C_{consistency} + 0.20 \cdot S_{grounding} + 0.20 \cdot Q_{comprehension}$$

---

## Quick Start

### Prerequisites

- **Python 3.11+** and **Node.js 18+**
- **OpenAI API key** (GPT-4o recommended; any OpenAI-compatible endpoint supported)

### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

### Configuration

All settings configurable via environment variables or `.env`:

| Variable | Default | Description |
|:---------|:--------|:------------|
| `OPENAI_API_KEY` | — | LLM API key *(required)* |
| `OPENAI_MODEL` | `gpt-4o` | Model identifier |
| `OPENAI_BASE_URL` | — | Custom endpoint (Azure, local, etc.) |

---

## User Flow

```
+------------+     +------------+     +------------+     +------------+
|   INPUT    |---->|   VERIFY   |---->|    QUIZ    |---->|   REPORT   |
|            |     |            |     |            |     |            |
|  Upload    |     |  9-step    |     |  Multi-    |     |  Overall   |
|  Paste     |     |  pipeline  |     |  level Qs  |     |  CI score  |
|  Generate  |     |  Real-time |     |  Graded    |     |  Risk map  |
|            |     |  streaming |     |  answers   |     |  Actions   |
+------------+     +------------+     +------------+     +------------+
```

1. **Document Input** — Upload a file, paste text, or generate via AI prompt
2. **Verification** — Watch the 9-node pipeline process facts in real-time via SSE streaming
3. **Comprehension Quiz** — Answer multi-level questions (recall, analysis, trap, scenario)
4. **Confidence Report** — Review composite CI score, risk areas, and actionable recommendations

---

## Research Foundations

GenDoc Confirm is informed by research in LLM verification and self-improvement. The following papers shaped the design, though the final pipeline optimizes and selectively applies their techniques:

| Paper | Year | Influence on Design |
|:------|:-----|:--------------------|
| **FActScore** — *Min et al.* | 2023 | Atomic fact decomposition for fine-grained evaluation (directly used) |
| **SAFE** — *Wei et al., Google DeepMind* | 2024 | Search-augmented factual evaluation with LLM agents (directly used) |
| **Chain-of-Verification (CoVe)** — *Dhuliawala et al.* | 2023 | Factored verification questions — applied in cross-examination (CoVe Lite) |
| **RARR** — *Gao et al.* | 2023 | Retrofit attribution via revision — merged into cross-reference step |
| **SelfCheckGPT** — *Manakul et al.* | 2023 | Multi-sample consistency concept — informed design, replaced by multi-perspective verification |
| **Reflexion** — *Shinn et al.* | 2023 | Verbal self-assessment concept — informed design, replaced by selective cross-examination |

---

## API Reference

### Core Endpoints

```http
POST   /api/v1/projects/                    # Create verification project
GET    /api/v1/projects/                    # List all projects
GET    /api/v1/projects/{id}               # Get project details

POST   /api/v1/projects/{id}/document      # Set document text or prompt
POST   /api/v1/projects/{id}/upload        # Upload document file
GET    /api/v1/projects/{id}/document      # Retrieve document

POST   /api/v1/projects/{id}/verify        # Start verification (SSE stream)
GET    /api/v1/projects/{id}/verify/results # Get verification results

GET    /api/v1/projects/{id}/quiz          # Get quiz questions
POST   /api/v1/projects/{id}/quiz/submit   # Submit quiz answers

GET    /api/v1/projects/{id}/report        # Get full confidence report
```

### SSE Event Types

| Event | Payload | Description |
|:------|:--------|:------------|
| `step_start` | `{step, label}` | Pipeline node begins execution |
| `fact_verified` | `{fact_id, status, confidence}` | Individual fact verification result |
| `step_complete` | `{step, label}` | Pipeline node finishes |
| `verification_complete` | `{message}` | Full pipeline complete |

---

## Testing

```bash
# Run end-to-end tests (requires running backend)
cd tests
pytest test_e2e.py -v --timeout=300
```

The E2E suite covers the complete lifecycle: project creation, document ingestion, SSE streaming verification, quiz generation, answer grading, and confidence report with all 4 scoring dimensions.

---

## Project Structure

```
Doc-Confirm/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI application entry point
│       ├── config.py                  # Pydantic settings
│       ├── store.py                   # In-memory project store
│       ├── agents/
│       │   └── graph.py               # 9-node LangGraph pipeline
│       ├── api/
│       │   ├── documents.py           # Document CRUD + file upload
│       │   ├── projects.py            # Project management
│       │   ├── verification.py        # SSE streaming verification
│       │   ├── quiz.py                # Comprehension quiz
│       │   └── reports.py             # Confidence reports
│       ├── models/
│       │   └── schemas.py             # Pydantic data models
│       ├── services/
│       │   ├── llm.py                 # LLM provider abstraction
│       │   └── parallel.py            # Parallel execution utilities
│       └── tools/
│           ├── fact_decomposer.py     # FActScore decomposition
│           ├── web_search.py          # Claim verification
│           ├── contradiction_detector.py
│           ├── cross_examiner.py      # CoVe-lite cross-examination
│           ├── evidence_checker.py    # Evidence grounding
│           └── quiz_generator.py      # Multi-level quiz generation
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── tailwind.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── components/layout/
│       │   └── MainLayout.tsx
│       ├── lib/
│       │   ├── api.ts                 # API client
│       │   └── types.ts               # TypeScript types
│       └── pages/
│           ├── Dashboard.tsx
│           ├── DocumentInput.tsx
│           ├── Verification.tsx
│           ├── Quiz.tsx
│           └── Report.tsx
├── tests/
│   └── test_e2e.py                    # End-to-end test suite
├── docker-compose.yml                 # Service orchestration
└── README.md
```

---

## Roadmap

- [ ] **Multi-model ensemble** — Cross-verify facts across GPT-4o, Claude, and Gemini
- [ ] **Domain-specific verification** — Specialized rules for medical, legal, and financial documents
- [ ] **Knowledge graph integration** — Structured fact storage with Neo4j
- [ ] **Collaborative review** — Multi-user verification workflows with role-based access
- [ ] **CI/CD integration** — Verify documentation in pull request pipelines
- [ ] **Plugin ecosystem** — Notion, Confluence, and Google Docs integrations
- [ ] **Database integration** — Connect PostgreSQL, Redis, and ChromaDB services to the application

---

<div align="center">

**Built with conviction that AI-generated content demands the same rigor we apply to human-authored work.**

*GenDoc Confirm — Trust, but verify.*

</div>

---

this readme is AI assisted generated, so check for mistakes
