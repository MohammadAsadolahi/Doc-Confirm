export type FactStatus = "verified" | "uncertain" | "hallucinated" | "unverifiable" | "checking";

export type QuestionType = "recall" | "analysis" | "application" | "trap" | "scenario";

export type IssueSeverity = "critical" | "warning" | "info";

export interface AtomicFact {
    id: string;
    text: string;
    category: string;
    positionStart: number;
    positionEnd: number;
    section: string;
}

export interface FactVerification {
    fact: AtomicFact;
    status: FactStatus;
    confidence: number;
    evidence: Evidence[];
    method: string;
    explanation: string;
}

export interface Evidence {
    source: string;
    text: string;
    url: string;
    relevance: number;
}

export interface ConsistencyIssue {
    type: string;
    factsInvolved: string[];
    explanation: string;
    severity: IssueSeverity;
}

export interface Question {
    id: string;
    text: string;
    type: QuestionType;
    relatedFacts: string[];
    options: string[] | null;
    correctAnswer: string;
    explanation: string;
    difficulty: "easy" | "medium" | "hard";
}

export interface ConfidenceReport {
    factualityScore: number;
    consistencyScore: number;
    sourceGroundingScore: number;
    comprehensionScore: number;
    overallConfidence: number;
    riskAreas: RiskArea[];
    recommendations: string[];
}

export interface RiskArea {
    severity: IssueSeverity;
    text: string;
    section: string;
}

export interface Project {
    id: string;
    name: string;
    description: string;
    status: "draft" | "verifying" | "quiz" | "complete";
    createdAt: string;
    updatedAt: string;
}
