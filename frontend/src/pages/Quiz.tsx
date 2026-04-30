import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    CheckCircle2,
    XCircle,
    ArrowRight,
    HelpCircle,
    AlertTriangle,
    Loader2,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";

interface QuizQuestion {
    id: string;
    text: string;
    type: "recall" | "analysis" | "application" | "trap" | "scenario";
    difficulty: string;
    options: string[];
}

export default function Quiz() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [questions, setQuestions] = useState<QuizQuestion[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentQ, setCurrentQ] = useState(0);
    const [selected, setSelected] = useState<number | null>(null);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [submitted, setSubmitted] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!id) return;
        api.quiz.get(id).then((data: any) => {
            setQuestions(data.questions || []);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (questions.length === 0) {
        return (
            <div className="text-center py-20 text-muted-foreground">
                No quiz questions available. Run verification first.
            </div>
        );
    }

    const question = questions[currentQ];
    const isLast = currentQ === questions.length - 1;

    const handleSelect = (idx: number) => {
        if (submitted) return;
        setSelected(idx);
        setAnswers((prev) => ({ ...prev, [question.id]: question.options[idx] }));
    };

    const handleNext = () => {
        if (isLast) return;
        setCurrentQ((prev) => prev + 1);
        setSelected(null);
    };

    const handleSubmitAll = async () => {
        if (!id) return;
        setSubmitting(true);
        try {
            const result = await api.quiz.submit(id, answers);
            setResults(result);
            setSubmitted(true);
        } catch (e) {
            console.error(e);
        }
        setSubmitting(false);
    };

    const typeColors: Record<string, string> = {
        recall: "text-blue-400",
        analysis: "text-purple-400",
        application: "text-green-400",
        trap: "text-red-400",
        scenario: "text-amber-400",
    };

    const typeLabels: Record<string, string> = {
        recall: "Recall",
        analysis: "Analysis",
        application: "Application",
        trap: "Trap Question",
        scenario: "Scenario",
    };

    if (submitted && results) {
        return (
            <div className="max-w-3xl mx-auto space-y-6">
                <h1 className="text-3xl font-bold text-foreground">Quiz Results</h1>
                <div className="glass-card text-center py-8">
                    <div className={`text-6xl font-bold ${results.score >= 0.8 ? "text-verified" : results.score >= 0.5 ? "text-uncertain" : "text-hallucinated"}`}>
                        {Math.round(results.score * 100)}%
                    </div>
                    <p className="text-muted-foreground mt-2">
                        {results.correct} / {results.total} correct
                    </p>
                </div>
                <div className="space-y-3">
                    {results.results?.map((r: any, i: number) => (
                        <div key={i} className={`glass-card flex items-start gap-3 ${r.correct ? "border-verified/20" : "border-hallucinated/20"}`}>
                            {r.correct ? <CheckCircle2 className="w-5 h-5 text-verified mt-0.5" /> : <XCircle className="w-5 h-5 text-hallucinated mt-0.5" />}
                            <div>
                                <p className="text-sm text-foreground">{questions[i]?.text}</p>
                                {!r.correct && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Correct: {r.correct_answer} | You said: {r.user_answer}
                                    </p>
                                )}
                                <p className="text-xs text-primary/80 mt-1">{r.explanation}</p>
                            </div>
                        </div>
                    ))}
                </div>
                <button
                    onClick={() => navigate(`/project/${id}/report`)}
                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-medium"
                >
                    View Report <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">
                    Step 3: Comprehension Quiz
                </h1>
                <p className="text-muted-foreground mt-1">
                    Prove you understand the document before sending it out
                </p>
            </div>

            <div className="flex gap-2">
                {questions.map((_, i) => (
                    <div
                        key={i}
                        className={`h-2 flex-1 rounded-full transition-all ${i < currentQ
                            ? "bg-primary"
                            : i === currentQ
                                ? "bg-primary/50"
                                : "bg-muted"
                            }`}
                    />
                ))}
            </div>

            <AnimatePresence mode="wait">
                <motion.div
                    key={currentQ}
                    initial={{ opacity: 0, x: 40 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -40 }}
                    className="glass-card space-y-6"
                >
                    <div className="flex items-center justify-between">
                        <span className={`text-xs font-medium uppercase tracking-wider ${typeColors[question.type] || "text-muted-foreground"}`}>
                            {question.type === "trap" && <AlertTriangle className="w-3 h-3 inline mr-1" />}
                            {typeLabels[question.type] || question.type}
                        </span>
                        <span className="text-sm text-muted-foreground">
                            {currentQ + 1} / {questions.length}
                        </span>
                    </div>

                    <h2 className="text-xl font-semibold text-foreground">{question.text}</h2>

                    <div className="space-y-3">
                        {question.options.map((option, i) => (
                            <button
                                key={i}
                                onClick={() => handleSelect(i)}
                                className={`w-full text-left p-4 rounded-xl border transition-all ${selected === i
                                    ? "border-primary bg-primary/10 text-foreground"
                                    : "border-border text-foreground hover:border-primary/50"
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${selected === i ? "border-primary bg-primary" : "border-border"}`} />
                                    <span className="text-sm">{option}</span>
                                </div>
                            </button>
                        ))}
                    </div>

                    <div className="flex justify-end gap-3">
                        {!isLast ? (
                            <button
                                onClick={handleNext}
                                disabled={selected === null}
                                className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium disabled:opacity-50"
                            >
                                Next <ArrowRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={handleSubmitAll}
                                disabled={selected === null || submitting}
                                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-medium disabled:opacity-50"
                            >
                                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                Submit All Answers
                            </button>
                        )}
                    </div>
                </motion.div>
            </AnimatePresence>
        </div>
    );
}
