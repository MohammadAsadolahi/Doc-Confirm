import { useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";

export default function DocumentInput() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [mode, setMode] = useState<"upload" | "paste" | "generate">("paste");
    const [content, setContent] = useState("");
    const [prompt, setPrompt] = useState("");
    const [submitting, setSubmitting] = useState(false);

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
