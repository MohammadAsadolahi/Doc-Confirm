# GenDoc Confirm — Implementation Plan

## AI-Generated Document Verification & Comprehension Assurance Platform

**App Name:** GenDoc Confirm  
**Stack:** React (Frontend) + Python/LangChain (Backend)  
**Core Value:** Ensure every AI-generated document is factually grounded, internally consistent, and fully understood by its creator before it goes anywhere.

---

## 1. Research Foundation & References

### 1.1 Key Research Papers

| Paper | Key Technique | How We Use It |
|-------|--------------|---------------|
| **SelfCheckGPT** (Manakul et al., 2023) | Sample multiple outputs, check consistency — no external knowledge needed | Core of our self-consistency hallucination detection |
| **Chain-of-Verification (CoVe)** (Dhuliawala et al., 2023) | Draft → Plan verification questions → Answer independently → Revise | Our 4-step verification pipeline |
| **FActScore** (Min et al., 2023) | Decompose text into atomic facts, validate each against knowledge source | Atomic fact scoring engine |
| **SAFE** (Wei et al., 2024) | LLM-as-agent issues search queries to verify facts iteratively | Search-augmented verification layer |
| **Reflexion** (Shinn et al., 2023) | Verbal self-reflection, episodic memory for better decision-making | Self-critique loop with memory |
| **LATS** (Zhou et al., 2023) | Monte Carlo Tree Search + self-reflection for LLM agents | Tree-search exploration of document alternatives |
| **RARR** (Gao et al., 2022) | Retrofit Attribution: Research & Revise model outputs | Post-generation attribution & correction |
| **FAVA** (Mishra et al., 2024) | Fine-grained hallucination detection with error taxonomy | Error categorization in our UI |
| **Lilian Weng's Survey** (Jul 2024) | Comprehensive taxonomy of hallucination causes, detection, mitigation | Architecture design blueprint |

### 1.2 Related Open Source Projects

- **google-deepmind/long-form-factuality** — LongFact prompts + SAFE evaluator
- **FacTool** (Chern et al., 2023) — Multi-domain factuality detection
- **LangChain/LangGraph** — Agent orchestration, tool calling, streaming
- **shadcn/ui** — AI-ready, composable React component library
- **Vercel AI SDK** — Streaming UI, generative component patterns

### 1.3 Key Blog Posts & Experience

- LangChain Blog: Deep Agents, Agent Harness Architecture, Human Judgment in Agent Loop
- Vercel Blog: AI SDK 3.0 Generative UI — streaming React components from LLMs
- shadcn/ui: AI-ready open code component system

---

## 2. Problem Statement & Value Proposition

### The Real-World Problem
Organizations generate thousands of AI documents (contracts, reports, proposals, compliance docs, medical summaries) but face three critical gaps:

1. **Hallucination Gap:** LLMs fabricate facts, statistics, citations, and entity details
2. **Consistency Gap:** Internal contradictions between sections go unnoticed
3. **Comprehension Gap:** The human who commissioned the document doesn't deeply understand what it says, leading to surprises with stakeholders

### Our Solution: A 3-Layer Verification System

```
┌─────────────────────────────────────────────────────┐
│                    GenDoc Confirm                     │
│                                                       │
│   Layer 1: AI Self-Verification (Automated)          │
│   ├── Chain-of-Verification (CoVe)                   │
│   ├── Self-Consistency Sampling (SelfCheckGPT)       │
│   ├── Atomic Fact Decomposition (FActScore)          │
│   └── Self-Critique & Reflexion Loop                 │
│                                                       │
│   Layer 2: Source-Grounded Verification              │
│   ├── RAG against provided source documents          │
│   ├── Web search verification (SAFE-style)           │
│   └── Cross-reference & citation checking            │
│                                                       │
│   Layer 3: Human Comprehension Assurance             │
│   ├── AI-generated comprehension questions           │
│   ├── Scenario-based "What would you say if..."      │
│   ├── Consistency trap questions (deliberate twists) │
│   └── Confidence calibration scoring                 │
└─────────────────────────────────────────────────────┘
```

### Why This Is Valuable
- **Legal/Compliance:** Before signing AI-drafted contracts, verify every clause
- **Medical:** Before sending AI-generated patient summaries, catch hallucinated drug names
- **Academic:** Before submitting AI-assisted papers, verify every citation exists
- **Business:** Before presenting AI reports to the board, ensure you can defend every claim

---

## 3. Architecture Overview

### 3.1 System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ Document  │  │ Verification │  │ Comprehension│  │Dashboard│ │
│  │ Editor    │  │ Report Panel │  │ Quiz Panel   │  │& Score  │ │
│  └─────┬────┘  └──────┬───────┘  └──────┬───────┘  └────┬────┘ │
│        │               │                 │               │       │
│        └───────────────┴────────┬────────┴───────────────┘       │
│                                 │ WebSocket / SSE                 │
│                                 ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    API Gateway (FastAPI)                     │ │
│  └──────────────────────┬───────────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────┐
│                   BACKEND (Python/LangChain)                     │
│                          │                                       │
│  ┌──────────────────────┴───────────────────────────────────┐   │
│  │              LangGraph Agent Orchestrator                 │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌───────────────────┐  │   │
│  │  │ Document    │ │ Verification │ │ Comprehension     │  │   │
│  │  │ Generation  │ │ Pipeline     │ │ Question Generator│  │   │
│  │  │ Agent       │ │ Agent        │ │ Agent             │  │   │
│  │  └──────┬──────┘ └──────┬───────┘ └────────┬──────────┘  │   │
│  │         │               │                   │              │   │
│  │         ▼               ▼                   ▼              │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │              Shared Tool Layer                       │  │   │
│  │  │  • LLM (OpenAI/Anthropic)  • Web Search            │  │   │
│  │  │  • Vector Store (ChromaDB)  • Citation Checker      │  │   │
│  │  │  • Fact Decomposer          • Consistency Analyzer  │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Storage: PostgreSQL + ChromaDB + Redis (session/cache)   │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 Tech Stack Detail

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 18+ with Vite | Fast DX, modern tooling |
| **UI Components** | shadcn/ui + Tailwind CSS + Framer Motion | Beautiful, accessible, AI-ready components |
| **State Management** | Zustand + React Query | Lightweight, server-state aware |
| **Real-time** | Server-Sent Events (SSE) | Streaming verification results |
| **Backend** | FastAPI (Python 3.11+) | Async, fast, great typing |
| **AI Orchestration** | LangChain + LangGraph | Agent workflows, tool orchestration |
| **LLM** | OpenAI GPT-4o / Anthropic Claude | Primary reasoning engine |
| **Vector Store** | ChromaDB | Local-first, easy setup |
| **Database** | PostgreSQL (via SQLAlchemy) | Documents, sessions, scores |
| **Cache** | Redis | Rate limiting, session cache |
| **Search** | Tavily / SerpAPI | Web verification |

---

## 4. Backend Pipeline Design (LangChain/LangGraph)

### 4.1 Core Pipeline: Chain-of-Verification + Self-Critique

```python
# Pseudocode of the main verification graph

class GenDocState(TypedDict):
    document: str                    # The AI-generated document
    source_materials: list[str]      # Optional source docs
    atomic_facts: list[AtomicFact]   # Decomposed claims
    verification_questions: list[str]
    verification_answers: list[VerificationResult]
    consistency_issues: list[Issue]
    hallucination_scores: dict
    self_critique: str
    revised_document: str
    comprehension_questions: list[Question]
    user_answers: list[Answer]
    comprehension_score: float
    confidence_report: ConfidenceReport

# LangGraph Workflow
graph = StateGraph(GenDocState)
graph.add_node("generate_document", generate_document_node)
graph.add_node("decompose_facts", decompose_atomic_facts)
graph.add_node("self_consistency_check", selfcheck_gpt_node)
graph.add_node("plan_verification", plan_verification_questions)
graph.add_node("execute_verification", execute_independent_verification)
graph.add_node("cross_reference", cross_reference_sources)
graph.add_node("self_critique", self_critique_and_reflect)
graph.add_node("revise_document", revise_with_findings)
graph.add_node("generate_quiz", generate_comprehension_quiz)
graph.add_node("evaluate_answers", evaluate_user_comprehension)
graph.add_node("final_report", compile_confidence_report)
```

### 4.2 Node Implementations

#### Node 1: Document Generation
```
Input: User prompt + optional source materials + style preferences
Process:
  1. Generate document with CoT reasoning
  2. Store generation metadata (model, temperature, timestamp)
  3. If source materials provided, ground generation via RAG
Output: Generated document with reasoning trace
```

#### Node 2: Atomic Fact Decomposition (FActScore-inspired)
```
Input: Generated document
Process:
  1. Break each paragraph into sentences
  2. Break each sentence into atomic facts (single verifiable claims)
  3. Categorize: factual claim / opinion / definition / citation / statistic
  4. Tag entities, dates, numbers, proper nouns
Output: List of AtomicFact objects with categories and positions
```

#### Node 3: Self-Consistency Check (SelfCheckGPT-inspired)
```
Input: Original prompt + generated document
Process:
  1. Re-generate document N times (N=5) at temperature=0.7
  2. For each atomic fact in original, check if it appears consistently across samples
  3. Score each fact: consistent (>4/5), partially consistent (2-4/5), inconsistent (<2/5)
  4. Flag inconsistent facts as likely hallucinations
Output: Per-fact consistency scores + flagged hallucinations
```

#### Node 4: Plan Verification Questions (CoVe Step 2)
```
Input: Document + atomic facts + consistency scores
Process:
  1. For each flagged/uncertain fact, generate a verification question
  2. For key claims, generate cross-checking questions
  3. For statistics, generate "source?" questions
  4. For citations, generate "does this exist?" questions
Output: Ordered list of verification questions
```

#### Node 5: Execute Verification (CoVe Step 3 - Factored)
```
Input: Verification questions (INDEPENDENTLY from original document)
Process:
  1. Answer each question separately (without seeing original document)
  2. For factual claims: search web via Tavily/SerpAPI
  3. For citations: check Google Scholar / CrossRef
  4. For statistics: verify against authoritative sources
  5. Compare independent answers with original document claims
Output: Per-question verification results with evidence
```

#### Node 6: Cross-Reference Sources
```
Input: Document + user-provided source materials
Process:
  1. Embed source materials in vector store
  2. For each atomic fact, retrieve most relevant source passages
  3. Check entailment (does source support the claim?)
  4. Flag unsupported claims and contradictions
Output: Source attribution map + unsupported claims
```

#### Node 7: Self-Critique & Reflexion
```
Input: All verification results + consistency scores + source attribution
Process:
  1. LLM reviews its own document with all evidence
  2. Identifies: what's wrong, what's uncertain, what's missing
  3. Generates verbal reflection (Reflexion-style)
  4. Proposes specific corrections
  5. If correction quality is low, iterate (max 3 times)
Output: Self-critique report + proposed corrections
```

#### Node 8: Revise Document
```
Input: Original document + self-critique + corrections
Process:
  1. Apply corrections while preserving style/intent (RARR-style)
  2. Mark changed sections with diff markers
  3. Add attribution footnotes where possible
  4. Re-run quick consistency check on revised version
Output: Revised document + diff + attribution report
```

#### Node 9: Generate Comprehension Quiz
```
Input: Final document + verification results
Process:
  1. Generate understanding questions at 3 levels:
     - Recall: "What does the document state about X?"
     - Analysis: "Why does the document recommend Y over Z?"
     - Application: "If a client asks about X, how would you respond?"
  2. Generate trap questions (deliberately wrong claims from the doc)
  3. Generate scenario questions ("Your manager asks about the claim on page 3...")
  4. Create multiple-choice + free-text mixed format
Output: Quiz with scoring rubric
```

#### Node 10: Evaluate & Report
```
Input: User quiz answers + scoring rubric + all verification data
Process:
  1. Score user answers against rubric
  2. Calculate comprehension percentage per section
  3. Identify knowledge gaps
  4. Generate final Confidence Report:
     - Document Factuality Score (0-100)
     - Internal Consistency Score (0-100)
     - Source Grounding Score (0-100)
     - User Comprehension Score (0-100)
     - Overall Confidence Index (weighted composite)
     - Risk areas & recommendations
Output: ConfidenceReport object
```

---

## 5. Frontend Design (React + shadcn/ui)

### 5.1 Application Flow

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   STEP 1    │────▶│   STEP 2     │────▶│   STEP 3      │
│   Upload/   │     │  AI Verifies │     │  You Answer   │
│   Generate  │     │  (Streaming) │     │  Questions    │
└─────────────┘     └──────────────┘     └───────────────┘
                                                │
                    ┌──────────────┐             │
                    │   STEP 4     │◀────────────┘
                    │  Confidence  │
                    │  Report      │
                    └──────────────┘
```

### 5.2 Page/Component Structure

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Landing / Dashboard
│   ├── projects/
│   │   ├── page.tsx                # Project list
│   │   └── [id]/
│   │       ├── page.tsx            # Project detail
│   │       ├── generate/page.tsx   # Step 1: Document input
│   │       ├── verify/page.tsx     # Step 2: Verification (streaming)
│   │       ├── quiz/page.tsx       # Step 3: Comprehension quiz
│   │       └── report/page.tsx     # Step 4: Final report
│   └── settings/page.tsx
├── components/
│   ├── ui/                         # shadcn/ui base components
│   ├── document/
│   │   ├── DocumentEditor.tsx      # Rich text editor with AI
│   │   ├── DocumentViewer.tsx      # Side-by-side diff view
│   │   ├── FactHighlighter.tsx     # Inline fact-status highlights
│   │   └── SourcePanel.tsx         # Source material upload
│   ├── verification/
│   │   ├── VerificationStream.tsx  # Live streaming verification
│   │   ├── FactCard.tsx            # Individual fact verification card
│   │   ├── ConsistencyMap.tsx      # Visual consistency graph
│   │   ├── HallucinationBadge.tsx  # Status badges
│   │   └── ProgressRing.tsx        # Animated progress indicator
│   ├── quiz/
│   │   ├── QuizCard.tsx            # Single question card
│   │   ├── ScenarioQuestion.tsx    # Scenario-based question
│   │   ├── TrapQuestion.tsx        # Trap question with explanation
│   │   └── QuizProgress.tsx        # Progress through quiz
│   ├── report/
│   │   ├── ConfidenceGauge.tsx     # Animated score gauge
│   │   ├── ScoreBreakdown.tsx      # Score by category
│   │   ├── RiskHeatmap.tsx         # Section-by-section risk
│   │   ├── RecommendationList.tsx  # Action items
│   │   └── ExportButton.tsx        # PDF/JSON export
│   └── shared/
│       ├── StreamingText.tsx       # Token-by-token streaming
│       ├── AnimatedCounter.tsx     # Number animation
│       └── GlassCard.tsx           # Glassmorphism card
├── hooks/
│   ├── useVerification.ts          # SSE connection to backend
│   ├── useQuiz.ts                  # Quiz state management
│   └── useProject.ts              # Project CRUD
├── stores/
│   ├── projectStore.ts             # Zustand project state
│   └── verificationStore.ts        # Verification results
└── lib/
    ├── api.ts                      # API client
    ├── sse.ts                      # SSE helper
    └── types.ts                    # Shared types
```

### 5.3 UI Design Principles

1. **Glassmorphism + Gradient Accents:** Modern frosted glass panels with subtle color gradients
2. **Dark Mode First:** Deep navy/charcoal background with glowing accent colors
3. **Micro-animations:** Framer Motion for every state transition, skeleton loaders, progress rings
4. **Traffic Light System:** Green/Yellow/Red for verification status at a glance
5. **Streaming UX:** Token-by-token text streaming, animated progress bars, live fact-checking indicators
6. **Split-Pane Document View:** Original vs. revised document side-by-side with inline diff

### 5.4 Key UI Screens

#### Screen 1: Document Input
- Drag-and-drop zone for documents (PDF, DOCX, TXT, MD)
- Rich text editor for paste/compose
- Source materials upload panel
- "Generate from prompt" option with prompt editor
- Style/tone selector

#### Screen 2: Live Verification Dashboard
- Central document view with colored annotations
- Left sidebar: Verification steps (animated progress)
- Right sidebar: Live fact-checking stream
- Bottom panel: Consistency map (network graph)
- Floating metrics: Real-time scores updating as checks complete
- Each fact gets a colored underline: 🟢 Verified | 🟡 Uncertain | 🔴 Hallucination

#### Screen 3: Comprehension Quiz
- Card-based quiz interface (one question per card, swipeable)
- Mix of multiple-choice, true/false, free-text, scenario-based
- Timer per question (optional)
- Instant feedback with document references
- "I don't know" option (honesty is valued)

#### Screen 4: Confidence Report
- Hero score: Large animated circular gauge (0-100)
- 4 sub-scores with animated progress rings
- Section-by-section heatmap
- Expandable issue cards with evidence
- Action item checklist
- Export to PDF with one click

---

## 6. API Design

### 6.1 REST + SSE Endpoints

```
POST   /api/projects                          # Create project
GET    /api/projects                          # List projects
GET    /api/projects/{id}                     # Get project details

POST   /api/projects/{id}/documents           # Upload/create document
POST   /api/projects/{id}/documents/generate  # Generate from prompt

POST   /api/projects/{id}/verify              # Start verification (returns SSE stream)
GET    /api/projects/{id}/verify/stream       # SSE endpoint for live results
GET    /api/projects/{id}/verify/results      # Get completed results

POST   /api/projects/{id}/quiz/generate       # Generate comprehension quiz
POST   /api/projects/{id}/quiz/submit         # Submit quiz answers
GET    /api/projects/{id}/quiz/results        # Get quiz results

GET    /api/projects/{id}/report              # Get full confidence report
POST   /api/projects/{id}/report/export       # Export report as PDF

POST   /api/documents/upload                  # Upload source materials
```

### 6.2 SSE Event Stream Format

```json
// During verification, events stream as:
{"event": "step_start", "data": {"step": "atomic_decomposition", "progress": 0.1}}
{"event": "fact_found", "data": {"id": "f1", "text": "Revenue grew 15%", "category": "statistic", "position": [45, 62]}}
{"event": "fact_verified", "data": {"id": "f1", "status": "uncertain", "confidence": 0.6, "evidence": "..."}}
{"event": "consistency_issue", "data": {"facts": ["f3", "f7"], "type": "contradiction", "explanation": "..."}}
{"event": "self_critique", "data": {"reflection": "...", "corrections": [...]}}
{"event": "step_complete", "data": {"step": "atomic_decomposition", "progress": 0.3}}
{"event": "verification_complete", "data": {"scores": {...}, "summary": "..."}}
```

---

## 7. Chain-of-Thought (CoT) & Self-Critique Design

### 7.1 CoT in Document Generation

Every generation step uses explicit CoT:
```
System: You are generating a {document_type}. Think step by step:
1. First, identify the key topics that must be covered
2. For each topic, determine what facts you are confident about
3. For facts you are uncertain about, explicitly state your uncertainty
4. Structure the document logically
5. For each claim, consider: "Can I attribute this to a specific source?"
6. Flag any statement where you are relying on general knowledge vs. specific data

Show your thinking process, then produce the document.
```

### 7.2 Self-Critique Prompting

After generating verification results:
```
System: You are a critical reviewer. Review your own verification work:

1. COMPLETENESS: Did I check every important claim? What did I miss?
2. RIGOR: Were my verification methods strong enough? Did I use the right tools?
3. BIAS: Am I being too lenient or too strict on certain types of claims?
4. GAPS: What additional checks would strengthen confidence?
5. CALIBRATION: Are my confidence scores well-calibrated?

Be brutally honest. The user's reputation depends on this document being correct.
```

### 7.3 Multi-Turn Self-Reflection Loop

```
Round 1: Generate initial assessment
Round 2: Critique the assessment → "I was too lenient on citation X because..."
Round 3: Address critique → Revise assessment + add missing checks
Round 4 (if needed): Final quality gate → "Is this report ready for the user?"
```

---

## 8. Data Models

### 8.1 Core Models

```python
class Project(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    status: Literal["draft", "verifying", "quiz", "complete"]
    document: Document
    verification_result: Optional[VerificationResult]
    quiz: Optional[Quiz]
    report: Optional[ConfidenceReport]

class Document(BaseModel):
    id: UUID
    content: str
    format: Literal["text", "markdown", "html"]
    source_materials: list[SourceMaterial]
    generation_metadata: Optional[GenerationMetadata]

class AtomicFact(BaseModel):
    id: str
    text: str
    category: Literal["factual_claim", "statistic", "citation", "definition", "opinion", "temporal"]
    position: tuple[int, int]  # start, end in document
    section: str

class VerificationResult(BaseModel):
    facts: list[FactVerification]
    consistency_issues: list[ConsistencyIssue]
    self_critique: SelfCritique
    revised_document: str
    scores: Scores

class FactVerification(BaseModel):
    fact: AtomicFact
    status: Literal["verified", "uncertain", "hallucinated", "unverifiable"]
    confidence: float  # 0.0 - 1.0
    evidence: list[Evidence]
    method: Literal["self_consistency", "web_search", "source_match", "citation_check"]

class ConsistencyIssue(BaseModel):
    type: Literal["contradiction", "ambiguity", "unsupported_inference", "temporal_inconsistency"]
    facts_involved: list[str]  # fact IDs
    explanation: str
    severity: Literal["critical", "warning", "info"]

class Question(BaseModel):
    id: str
    text: str
    type: Literal["recall", "analysis", "application", "trap", "scenario"]
    related_facts: list[str]  # fact IDs
    options: Optional[list[str]]  # for multiple choice
    correct_answer: str
    explanation: str
    difficulty: Literal["easy", "medium", "hard"]

class ConfidenceReport(BaseModel):
    factuality_score: float      # 0-100
    consistency_score: float     # 0-100
    source_grounding_score: float # 0-100
    comprehension_score: float   # 0-100
    overall_confidence: float    # weighted composite
    risk_areas: list[RiskArea]
    recommendations: list[str]
    timestamp: datetime
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up monorepo structure (frontend + backend)
- [ ] Initialize React project with Vite + shadcn/ui + Tailwind
- [ ] Initialize FastAPI backend with project structure
- [ ] Set up PostgreSQL + ChromaDB
- [ ] Implement basic document upload/create API
- [ ] Build document editor and viewer components
- [ ] Set up LangChain with OpenAI/Anthropic

### Phase 2: Verification Engine (Week 3-4)
- [ ] Implement atomic fact decomposition node
- [ ] Implement self-consistency check (SelfCheckGPT)
- [ ] Implement CoVe verification pipeline
- [ ] Add web search verification (Tavily integration)
- [ ] Build SSE streaming from backend to frontend
- [ ] Create live verification dashboard UI
- [ ] Implement fact highlighting in document viewer

### Phase 3: Self-Critique & Revision (Week 5)
- [ ] Implement self-critique Reflexion loop
- [ ] Build document revision with diff tracking
- [ ] Add source attribution engine
- [ ] Create consistency analysis (cross-section checks)
- [ ] Build consistency map visualization

### Phase 4: Comprehension Quiz (Week 6)
- [ ] Implement quiz generation agent
- [ ] Build recall, analysis, application question generators
- [ ] Add trap question generator
- [ ] Create scenario-based question generator
- [ ] Build quiz UI with card-based interface
- [ ] Implement quiz scoring and feedback

### Phase 5: Confidence Report (Week 7)
- [ ] Build composite scoring algorithm
- [ ] Create animated confidence report UI
- [ ] Implement section-by-section heatmap
- [ ] Add PDF export functionality
- [ ] Build recommendation engine
- [ ] Add historical comparison (track improvement over time)

### Phase 6: Polish & Production (Week 8)
- [ ] Add authentication (NextAuth or Clerk)
- [ ] Performance optimization (caching, batching)
- [ ] Error handling and retry logic
- [ ] Responsive design for mobile
- [ ] End-to-end testing
- [ ] Deployment setup (Docker + cloud)

---

## 10. Project File Structure

```
gendoc-confirm/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css                 # Tailwind + custom styles
│       ├── components/
│       │   ├── ui/                   # shadcn/ui components
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Header.tsx
│       │   │   └── MainLayout.tsx
│       │   ├── document/
│       │   │   ├── DocumentEditor.tsx
│       │   │   ├── DocumentViewer.tsx
│       │   │   ├── FactHighlighter.tsx
│       │   │   ├── DiffView.tsx
│       │   │   └── SourceUpload.tsx
│       │   ├── verification/
│       │   │   ├── VerificationDashboard.tsx
│       │   │   ├── VerificationStream.tsx
│       │   │   ├── FactCard.tsx
│       │   │   ├── ConsistencyGraph.tsx
│       │   │   └── ScoreRing.tsx
│       │   ├── quiz/
│       │   │   ├── QuizContainer.tsx
│       │   │   ├── QuestionCard.tsx
│       │   │   ├── QuizResults.tsx
│       │   │   └── QuizProgress.tsx
│       │   └── report/
│       │       ├── ConfidenceReport.tsx
│       │       ├── ScoreGauge.tsx
│       │       ├── RiskHeatmap.tsx
│       │       └── ExportPanel.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── ProjectDetail.tsx
│       │   ├── DocumentInput.tsx
│       │   ├── Verification.tsx
│       │   ├── Quiz.tsx
│       │   └── Report.tsx
│       ├── hooks/
│       │   ├── useSSE.ts
│       │   ├── useVerification.ts
│       │   ├── useQuiz.ts
│       │   └── useProject.ts
│       ├── stores/
│       │   ├── projectStore.ts
│       │   └── uiStore.ts
│       ├── lib/
│       │   ├── api.ts
│       │   ├── types.ts
│       │   └── utils.ts
│       └── styles/
│           └── globals.css
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry
│   │   ├── config.py                 # Settings
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── document.py
│   │   │   ├── verification.py
│   │   │   └── quiz.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py
│   │   │   ├── documents.py
│   │   │   ├── verification.py
│   │   │   ├── quiz.py
│   │   │   └── reports.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py              # LangGraph orchestrator
│   │   │   ├── document_agent.py     # Document generation
│   │   │   ├── verification_agent.py # Fact verification
│   │   │   ├── critique_agent.py     # Self-critique
│   │   │   └── quiz_agent.py         # Quiz generation
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── fact_decomposer.py
│   │   │   ├── self_consistency.py
│   │   │   ├── web_search.py
│   │   │   ├── citation_checker.py
│   │   │   └── source_matcher.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py
│   │   │   ├── vector_store.py
│   │   │   └── scoring.py
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── database.py
│   │       └── migrations/
│   └── tests/
│       ├── test_verification.py
│       ├── test_quiz.py
│       └── test_api.py
├── docker-compose.yml
├── .env.example
├── README.md
└── IMPLEMENTATION_PLAN.md            # This file
```

---

## 11. Key Algorithms & Prompts

### 11.1 Atomic Fact Decomposition Prompt
```
Given the following text, break it down into atomic facts.
Each atomic fact should be a single, verifiable claim.

Rules:
- One fact per line
- Each fact should be independently verifiable
- Include the exact text span from the original
- Categorize as: factual_claim | statistic | citation | definition | opinion | temporal

Text: {document_text}

Output as JSON array.
```

### 11.2 Comprehension Question Generation Prompt
```
You are creating a comprehension test for someone who should fully understand
this document before presenting it to stakeholders.

Document: {document}
Verification findings: {findings}

Generate questions at three levels:

RECALL (3 questions): Test whether they remember key facts
ANALYSIS (3 questions): Test whether they understand WHY and HOW
APPLICATION (3 questions): Test whether they can defend/explain in real scenarios

Also generate:
TRAP (2 questions): Present a slightly wrong version of a fact from the doc.
  The correct answer is to identify it as wrong.
SCENARIO (2 questions): "Your CEO asks you about X. What do you say?"

For each question, provide:
- The question text
- Correct answer
- Explanation referencing specific parts of the document
- Related fact IDs for traceability
```

### 11.3 Consistency Analysis Prompt
```
Analyze this document for internal consistency. Look for:

1. CONTRADICTIONS: Two statements that cannot both be true
2. AMBIGUITIES: Statements that could be interpreted in conflicting ways  
3. UNSUPPORTED INFERENCES: Conclusions not supported by the stated premises
4. TEMPORAL ISSUES: Timeline contradictions or anachronisms
5. NUMERICAL ISSUES: Math that doesn't add up, percentages that don't total 100%
6. ENTITY CONFUSION: Same entity referred to inconsistently

Document: {document}

For each issue found, provide:
- Type of issue
- Exact text spans involved
- Severity (critical/warning/info)  
- Explanation of the inconsistency
```

---

## 12. Self-Critique Loop Design

```
┌──────────────────────────────────────────────────────────────┐
│                    Self-Critique Loop                          │
│                                                                │
│  ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌────────┐ │
│  │ Generate │───▶│ Evaluate │───▶│ Critique  │───▶│ Revise │ │
│  │ Result   │    │ Quality  │    │ Weaknesses│    │ Result │ │
│  └─────────┘    └──────────┘    └───────────┘    └───┬────┘ │
│       ▲                                              │       │
│       │              Quality Gate                     │       │
│       │         ┌──────────────────┐                 │       │
│       └─────────│ Score < Threshold│◀────────────────┘       │
│                 │ AND loops < 3    │                          │
│                 └──────────────────┘                          │
│                         │ PASS                               │
│                         ▼                                    │
│                  ┌──────────────┐                            │
│                  │ Final Output │                            │
│                  └──────────────┘                            │
└──────────────────────────────────────────────────────────────┘

Quality Criteria:
  - Fact coverage > 90%
  - No critical inconsistencies missed
  - All citations checked
  - Self-consistency score > 0.7
  - Clear evidence for each verdict
```

---

## 13. Scoring Algorithm

```python
def calculate_confidence(verification: VerificationResult, quiz: QuizResult) -> ConfidenceReport:
    # Factuality: % of atomic facts verified as correct
    factuality = (verified_count / total_facts) * 100
    
    # Consistency: inverse of consistency issues weighted by severity
    consistency_penalty = (
        critical_issues * 20 +
        warning_issues * 10 +
        info_issues * 2
    )
    consistency = max(0, 100 - consistency_penalty)
    
    # Source Grounding: % of claims with source attribution
    grounding = (attributed_facts / total_facts) * 100
    
    # Comprehension: weighted quiz score
    comprehension = (
        recall_score * 0.2 +
        analysis_score * 0.3 +
        application_score * 0.3 +
        trap_score * 0.1 +
        scenario_score * 0.1
    ) * 100
    
    # Overall: weighted composite
    overall = (
        factuality * 0.30 +
        consistency * 0.25 +
        grounding * 0.20 +
        comprehension * 0.25
    )
    
    return ConfidenceReport(
        factuality_score=factuality,
        consistency_score=consistency,
        source_grounding_score=grounding,
        comprehension_score=comprehension,
        overall_confidence=overall,
        risk_areas=identify_risks(...),
        recommendations=generate_recommendations(...)
    )
```

---

## 14. Security Considerations

1. **Input Sanitization:** All document inputs sanitized against XSS and injection
2. **API Key Management:** LLM API keys stored in environment variables, never exposed to frontend
3. **Rate Limiting:** Redis-based rate limiting per user/IP
4. **Authentication:** JWT-based auth with refresh tokens
5. **Data Privacy:** Documents stored encrypted at rest, option for ephemeral processing
6. **Prompt Injection Protection:** Input documents scanned for potential prompt injection patterns
7. **CORS:** Strict origin policy
8. **File Upload:** Type validation, size limits, virus scanning

---

## 15. Deployment

```yaml
# docker-compose.yml overview
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, chromadb]
  
  postgres:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]
  
  redis:
    image: redis:7-alpine
  
  chromadb:
    image: chromadb/chroma
    ports: ["8001:8000"]
```

---

## 16. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Hallucination Detection Rate | >85% recall | Compared against human annotation on test set |
| False Positive Rate | <15% | Manual review of flagged facts |
| Verification Latency | <60s for 2-page doc | End-to-end timing |
| Quiz Relevance | >90% relevant questions | User feedback rating |
| User Comprehension Lift | +30% vs. no quiz | Before/after comprehension test |
| User Satisfaction | >4.2/5 | Post-session survey |

---

## 17. Future Enhancements

1. **Multi-language Support:** Verify documents in any language
2. **Domain-Specific Verification:** Legal, medical, financial specialized checkers
3. **Team Collaboration:** Multiple reviewers, shared verification results
4. **API Integration:** Plug into existing document workflows (Google Docs, Notion, Confluence)
5. **Fine-tuned Models:** Train smaller models on verification data for speed/cost
6. **Continuous Learning:** Track which hallucinations users catch that the system missed
7. **Regulatory Compliance:** Map to specific compliance frameworks (SOC2, HIPAA, GDPR)
8. **Version Comparison:** Track how documents evolve through verification cycles

---

*This plan was synthesized from research across 10+ academic papers, multiple open-source projects, and industry best practices in AI safety, hallucination detection, and human-AI interaction design.*
