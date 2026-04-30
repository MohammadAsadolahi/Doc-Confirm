import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Shield,
    CheckCircle2,
    AlertTriangle,
    XCircle,
    Loader2,
    ArrowRight,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

type FactStatus = "verified" | "uncertain" | "hallucinated" | "checking";

interface Fact {
    id: string;
    text: string;
    status: FactStatus;
    confidence: number;
}

interface StepInfo {
    key: string;
    label: string;
    status: "pending" | "running" | "done";
}

const statusIcon = {
    verified: <CheckCircle2 className="w-4 h-4 text-verified" />,
    uncertain: <AlertTriangle className="w-4 h-4 text-uncertain" />,
    hallucinated: <XCircle className="w-4 h-4 text-hallucinated" />,
    checking: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
};

const PIPELINE_STEPS = [
    { key: "generate_document", label: "Generating Document" },
    { key: "decompose_facts", label: "Decomposing into Atomic Facts" },
    { key: "self_consistency_check", label: "Self-Consistency Check" },
    { key: "plan_verification", label: "Planning Verification" },
    { key: "execute_verification", label: "Verifying Facts" },
    { key: "cross_reference", label: "Contradiction Detection" },
    { key: "self_critique", label: "Self-Critique (Reflexion)" },
    { key: "revise_document", label: "Revising Document" },
    { key: "generate_quiz", label: "Generating Quiz" },
    { key: "evaluate_answers", label: "Evaluating Comprehension" },
    { key: "final_report", label: "Compiling Report" },
];

export default function Verification() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [steps, setSteps] = useState<StepInfo[]>(
        PIPELINE_STEPS.map((s) => ({ ...s, status: "pending" as const }))
    );
    const [facts, setFacts] = useState<Fact[]>([]);
    const [complete, setComplete] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const started = useRef(false);

    const processSSE = useCallback(async () => {
        if (!id || started.current) return;
        started.current = true;

        try {
            const response = await fetch(`/api/projects/${id}/verify`, {
                method: "POST",
                headers: { Accept: "text/event-stream" },
            });

            if (!response.ok || !response.body) {
                setError(`Verification failed: ${response.statusText}`);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let eventType = "";
            let dataStr = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    const trimmed = line.replace(/\r$/, "");
                    if (trimmed.startsWith("event:")) {
                        eventType = trimmed.slice(6).trim();
                    } else if (trimmed.startsWith("data:")) {
                        dataStr = trimmed.slice(5).trim();
                    } else if (trimmed === "" && eventType && dataStr) {
                        try {
                            const data = JSON.parse(dataStr);
                            handleEvent(eventType, data);
                        } catch { }
                        eventType = "";
                        dataStr = "";
                    }
                }
            }
        } catch (e: any) {
            setError(e.message || "Connection error");
        }
    }, [id]);

    const handleEvent = (event: string, data: any) => {
        if (event === "step_start") {
            setSteps((prev) =>
                prev.map((s) =>
                    s.key === data.step ? { ...s, label: data.label || s.label, status: "running" } : s
                )
            );
        } else if (event === "step_complete") {
            setSteps((prev) =>
                prev.map((s) =>
                    s.key === data.step ? { ...s, status: "done" } : s
                )
            );

            // Handle facts from decompose step
            if (data.step === "decompose_facts" && data.data?.facts) {
                setFacts(
                    data.data.facts.map((f: any) => ({
                        id: f.id,
                        text: f.text,
                        status: "checking" as FactStatus,
                        confidence: 0,
                    }))
                );
            }

            if (data.step === "final_report") {
                setComplete(true);
            }
        } else if (event === "fact_verified") {
            setFacts((prev) =>
                prev.map((f) =>
                    f.id === data.fact_id
                        ? { ...f, status: data.status as FactStatus, confidence: data.confidence }
                        : f
                )
            );
        } else if (event === "verification_complete") {
            setComplete(true);
        } else if (event === "error") {
            setError(data.error || "Unknown error");
        }
    };

    useEffect(() => {
        processSSE();
    }, [processSSE]);

    const scores = {
        verified: facts.filter((f) => f.status === "verified").length,
        uncertain: facts.filter((f) => f.status === "uncertain").length,
        hallucinated: facts.filter((f) => f.status === "hallucinated").length,
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground">
                        Step 2: Verification
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        AI is analyzing your document for hallucinations and inconsistencies
                    </p>
                </div>
                {complete && (
                    <motion.button
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        onClick={() => navigate(`/project/${id}/quiz`)}
                        className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-medium"
                    >
                        Take Comprehension Quiz
                        <ArrowRight className="w-4 h-4" />
                    </motion.button>
                )}
            </div>

            {error && (
                <div className="glass-card border-hallucinated/30 bg-hallucinated/5 text-hallucinated">
                    {error}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="glass-card space-y-3">
                    <h3 className="font-semibold text-foreground flex items-center gap-2">
                        <Shield className="w-4 h-4 text-primary" />
                        Verification Pipeline
                    </h3>
                    {steps.map((step, i) => (
                        <motion.div
                            key={step.key}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className={`flex items-center gap-3 text-sm p-2 rounded-lg ${step.status === "running"
                                ? "bg-primary/10 text-primary"
                                : step.status === "done"
                                    ? "text-verified"
                                    : "text-muted-foreground"
                                }`}
                        >
                            {step.status === "done" ? (
                                <CheckCircle2 className="w-4 h-4" />
                            ) : step.status === "running" ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <div className="w-4 h-4 rounded-full border border-current" />
                            )}
                            {step.label}
                        </motion.div>
                    ))}
                </div>

                <div className="lg:col-span-2 glass-card">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-foreground">
                            Atomic Facts Verified
                        </h3>
                        <div className="flex gap-4 text-sm">
                            <span className="text-verified">{scores.verified} verified</span>
                            <span className="text-uncertain">{scores.uncertain} uncertain</span>
                            <span className="text-hallucinated">{scores.hallucinated} hallucinated</span>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <AnimatePresence>
                            {facts.map((fact) => (
                                <motion.div
                                    key={fact.id}
                                    initial={{ opacity: 0, y: 10, height: 0 }}
                                    animate={{ opacity: 1, y: 0, height: "auto" }}
                                    exit={{ opacity: 0 }}
                                    className={`flex items-start gap-3 p-3 rounded-lg border ${fact.status === "verified"
                                        ? "border-verified/20 bg-verified/5"
                                        : fact.status === "uncertain"
                                            ? "border-uncertain/20 bg-uncertain/5"
                                            : fact.status === "hallucinated"
                                                ? "border-hallucinated/20 bg-hallucinated/5"
                                                : "border-blue-400/20 bg-blue-400/5"
                                        }`}
                                >
                                    {statusIcon[fact.status]}
                                    <div className="flex-1">
                                        <p className="text-sm text-foreground">{fact.text}</p>
                                        {fact.status !== "checking" && (
                                            <div className="flex items-center gap-2 mt-1">
                                                <div className="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
                                                    <motion.div
                                                        className={`h-full rounded-full ${fact.confidence > 0.8
                                                            ? "bg-verified"
                                                            : fact.confidence > 0.5
                                                                ? "bg-uncertain"
                                                                : "bg-hallucinated"
                                                            }`}
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${fact.confidence * 100}%` }}
                                                        transition={{ duration: 0.5 }}
                                                    />
                                                </div>
                                                <span className="text-xs text-muted-foreground">
                                                    {Math.round(fact.confidence * 100)}%
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        {facts.length === 0 && !error && (
                            <div className="text-center py-8 text-muted-foreground">
                                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                                Waiting for verification pipeline...
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
