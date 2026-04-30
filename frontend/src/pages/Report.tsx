import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Shield,
    FileCheck,
    Link2,
    Brain,
    AlertTriangle,
    CheckCircle2,
    Loader2,
} from "lucide-react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";

function ScoreRing({ score, color, size = 120 }: { score: number; color: string; size?: number }) {
    const radius = (size - 12) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    return (
        <div className="relative" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="score-ring">
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
                <motion.circle
                    cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={circumference}
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
                <motion.span className="text-2xl font-bold text-foreground" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
                    {score}
                </motion.span>
            </div>
        </div>
    );
}

export default function Report() {
    const { id } = useParams();
    const [report, setReport] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        api.report.get(id).then((data: any) => {
            setReport(data);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, [id]);

    if (loading) {
        return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
    }

    if (!report?.report) {
        return <div className="text-center py-20 text-muted-foreground">No report available yet.</div>;
    }

    const r = report.report;
    const overallScore = Math.round((r.overall_confidence || 0) * 100);

    const scores = [
        { label: "Factuality", score: Math.round((r.factuality_score || 0) * 100), icon: Shield, color: "#22c55e" },
        { label: "Consistency", score: Math.round((r.consistency_score || 0) * 100), icon: FileCheck, color: "#3b82f6" },
        { label: "Source Grounding", score: Math.round((r.source_grounding_score || 0) * 100), icon: Link2, color: "#a855f7" },
        { label: "Comprehension", score: Math.round((r.comprehension_score || 0) * 100), icon: Brain, color: "#eab308" },
    ];

    const risks = r.risk_areas || [];
    const recommendations = r.recommendations || [];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">Step 4: Confidence Report</h1>
                <p className="text-muted-foreground mt-1">Your document's verification summary</p>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card flex flex-col items-center py-8">
                <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">Overall Confidence Index</h2>
                <ScoreRing score={overallScore} color={overallScore >= 80 ? "#22c55e" : overallScore >= 60 ? "#eab308" : "#ef4444"} size={160} />
                <p className="mt-4 text-muted-foreground text-sm">
                    {overallScore >= 80 ? "Good confidence — minor issues to address" : overallScore >= 60 ? "Moderate confidence — review flagged items" : "Low confidence — significant corrections needed"}
                </p>
            </motion.div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {scores.map((s, i) => (
                    <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.1 }} className="glass-card flex flex-col items-center">
                        <s.icon className="w-5 h-5 mb-2" style={{ color: s.color }} />
                        <ScoreRing score={s.score} color={s.color} size={80} />
                        <span className="text-xs text-muted-foreground mt-2">{s.label}</span>
                    </motion.div>
                ))}
            </div>

            {risks.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="glass-card">
                    <h3 className="font-semibold text-foreground flex items-center gap-2 mb-4">
                        <AlertTriangle className="w-4 h-4 text-uncertain" /> Risk Areas
                    </h3>
                    <div className="space-y-3">
                        {risks.map((risk: any, i: number) => (
                            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg ${risk.status === "hallucinated" ? "bg-hallucinated/10 border border-hallucinated/20" : "bg-uncertain/10 border border-uncertain/20"}`}>
                                <AlertTriangle className={`w-4 h-4 mt-0.5 ${risk.status === "hallucinated" ? "text-hallucinated" : "text-uncertain"}`} />
                                <div>
                                    <p className="text-sm text-foreground">{risk.fact}</p>
                                    <span className="text-xs text-muted-foreground">{risk.status} — {Math.round((risk.confidence || 0) * 100)}% confidence</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }} className="glass-card">
                <h3 className="font-semibold text-foreground flex items-center gap-2 mb-4">
                    <CheckCircle2 className="w-4 h-4 text-verified" /> Recommendations
                </h3>
                <div className="space-y-2">
                    {recommendations.map((rec: string, i: number) => (
                        <div key={i} className="flex items-start gap-3 p-2">
                            <span className="text-primary font-mono text-sm">{i + 1}.</span>
                            <p className="text-sm text-foreground">{rec}</p>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    );
}
