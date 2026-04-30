import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Sparkles, ArrowRight, Loader2, BookOpen, X, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";

interface EvidenceItem {
    id?: string;
    label: string;
    content: string;
    saved: boolean;
}

export default function DocumentInput() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [mode, setMode] = useState<"upload" | "paste" | "generate">("paste");
    const [content, setContent] = useState("");
    const [prompt, setPrompt] = useState("");
    const [submitting, setSubmitting] = useState(false);

    // Evidence state
    const [evidenceExpanded, setEvidenceExpanded] = useState(false);
    const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);
    const [newEvidenceLabel, setNewEvidenceLabel] = useState("");
    const [newEvidenceContent, setNewEvidenceContent] = useState("");
    const [savingEvidence, setSavingEvidence] = useState(false);

    const handleAddEvidence = async () => {
        if (!id || !newEvidenceContent.trim()) return;
        setSavingEvidence(true);
        try {
            const res = await api.evidence.add(id, {
                label: newEvidenceLabel || `Evidence ${evidenceItems.length + 1}`,
                content: newEvidenceContent,
            });
            setEvidenceItems((prev) => [
                ...prev,
                { id: res.evidence_id, label: newEvidenceLabel || `Evidence ${prev.length + 1}`, content: newEvidenceContent, saved: true },
            ]);
            setNewEvidenceLabel("");
            setNewEvidenceContent("");
        } catch (e) {
            console.error(e);
        }
        setSavingEvidence(false);
    };

    const handleEvidenceFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const text = await file.text();
        setNewEvidenceLabel(file.name);
        setNewEvidenceContent(text);
    };

    const handleRemoveEvidence = async (index: number) => {
        const item = evidenceItems[index];
        if (item.id && id) {
            try {
                await api.evidence.remove(id, item.id);
            } catch (e) {
                console.error(e);
            }
        }
        setEvidenceItems((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async () => {
        if (!id) return;
        setSubmitting(true);
        try {
            if (mode === "paste" && content) {
                await api.documents.set(id, { document: content });
            } else if (mode === "generate" && prompt) {
                await api.documents.set(id, { prompt });
            }
            navigate(`/project/${id}/verify`);
        } catch (e) {
            console.error(e);
            setSubmitting(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !id) return;
        const text = await file.text();
        setContent(text);
        setMode("paste");
    };

    const canSubmit = mode === "paste" ? content.trim().length > 0 : prompt.trim().length > 0;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">
                    Step 1: Document Input
                </h1>
                <p className="text-muted-foreground mt-1">
                    Upload, paste, or generate the document you want to verify
                </p>
            </div>

            <div className="flex gap-2">
                {[
                    { key: "upload", label: "Upload", icon: Upload },
                    { key: "paste", label: "Paste Text", icon: FileText },
                    { key: "generate", label: "AI Generate", icon: Sparkles },
                ].map((m) => (
                    <button
                        key={m.key}
                        onClick={() => setMode(m.key as typeof mode)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${mode === m.key
                            ? "bg-primary text-primary-foreground"
                            : "glass text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        <m.icon className="w-4 h-4" />
                        {m.label}
                    </button>
                ))}
            </div>

            <motion.div
                key={mode}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card"
            >
                {mode === "upload" && (
                    <div className="border-2 border-dashed border-border rounded-xl p-12 text-center">
                        <Upload className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                        <p className="text-foreground font-medium">
                            Drop your document here
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">
                            TXT or Markdown
                        </p>
                        <input type="file" className="hidden" id="file-upload" accept=".txt,.md,.markdown" onChange={handleFileUpload} />
                        <label
                            htmlFor="file-upload"
                            className="mt-4 inline-block px-4 py-2 bg-primary text-primary-foreground rounded-lg cursor-pointer text-sm"
                        >
                            Browse Files
                        </label>
                    </div>
                )}

                {mode === "paste" && (
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Paste your AI-generated document here..."
                        className="w-full h-64 bg-transparent border border-border rounded-xl p-4 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                )}

                {mode === "generate" && (
                    <div className="space-y-4">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe the document you want to generate... e.g. 'Write a quarterly revenue report for a SaaS company with $5M ARR'"
                            className="w-full h-40 bg-transparent border border-border rounded-xl p-4 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                        />
                    </div>
                )}
            </motion.div>

            {/* Evidence / Reference Materials (Optional) */}
            <div className="glass-card">
                <button
                    onClick={() => setEvidenceExpanded(!evidenceExpanded)}
                    className="w-full flex items-center justify-between text-left"
                >
                    <div className="flex items-center gap-2">
                        <BookOpen className="w-5 h-5 text-primary" />
                        <div>
                            <span className="font-semibold text-foreground">Evidence / Reference Materials</span>
                            <span className="text-xs text-muted-foreground ml-2">(optional)</span>
                        </div>
                        {evidenceItems.length > 0 && (
                            <span className="ml-2 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                                {evidenceItems.length} added
                            </span>
                        )}
                    </div>
                    {evidenceExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                </button>

                <AnimatePresence>
                    {evidenceExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <p className="text-sm text-muted-foreground mt-3 mb-4">
                                Provide source documents, research papers, or reference materials to verify the document against.
                                Facts will be checked against your evidence for grounding.
                            </p>

                            {/* Existing evidence items */}
                            {evidenceItems.length > 0 && (
                                <div className="space-y-2 mb-4">
                                    {evidenceItems.map((item, i) => (
                                        <div key={i} className="flex items-center gap-2 p-2 rounded-lg border border-border bg-muted/30">
                                            <FileText className="w-4 h-4 text-verified flex-shrink-0" />
                                            <span className="text-sm text-foreground flex-1 truncate">{item.label}</span>
                                            <span className="text-xs text-muted-foreground">{item.content.length.toLocaleString()} chars</span>
                                            <button onClick={() => handleRemoveEvidence(i)} className="text-muted-foreground hover:text-hallucinated">
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Add new evidence */}
                            <div className="space-y-3 border-t border-border pt-3">
                                <div className="flex gap-2">
                                    <input
                                        value={newEvidenceLabel}
                                        onChange={(e) => setNewEvidenceLabel(e.target.value)}
                                        placeholder="Label (e.g., 'Q4 Financial Data')"
                                        className="flex-1 bg-transparent border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                    <input type="file" className="hidden" id="evidence-upload" accept=".txt,.md,.csv,.json" onChange={handleEvidenceFileUpload} />
                                    <label htmlFor="evidence-upload" className="flex items-center gap-1 px-3 py-2 glass text-sm text-muted-foreground hover:text-foreground rounded-lg cursor-pointer">
                                        <Upload className="w-3 h-3" /> File
                                    </label>
                                </div>
                                <textarea
                                    value={newEvidenceContent}
                                    onChange={(e) => setNewEvidenceContent(e.target.value)}
                                    placeholder="Paste reference material, source data, research excerpts..."
                                    className="w-full h-32 bg-transparent border border-border rounded-xl p-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                                />
                                <button
                                    onClick={handleAddEvidence}
                                    disabled={!newEvidenceContent.trim() || savingEvidence}
                                    className="flex items-center gap-1 px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 disabled:opacity-50"
                                >
                                    {savingEvidence ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                                    Add Evidence
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="flex justify-end">
                <button
                    onClick={handleSubmit}
                    disabled={!canSubmit || submitting}
                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    Start Verification
                    <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}
