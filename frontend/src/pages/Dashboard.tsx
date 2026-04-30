import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus, FolderOpen, Shield, Clock, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

const statusColors: Record<string, string> = {
    draft: "text-muted-foreground",
    verifying: "text-yellow-400",
    quiz: "text-blue-400",
    complete: "text-green-400",
};

export default function Dashboard() {
    const navigate = useNavigate();
    const [projects, setProjects] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        api.projects.list().then((data) => {
            setProjects(data);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    const handleCreate = async () => {
        setCreating(true);
        try {
            const project = await api.projects.create({
                name: "New Verification Project",
                description: "",
            });
            navigate(`/project/${project.id}/input`);
        } catch {
            setCreating(false);
        }
    };

    return (
        <div className="space-y-8">
            <div className="text-center space-y-4 py-8">
                <motion.h1
                    className="text-5xl font-bold gradient-text"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    GenDoc Confirm
                </motion.h1>
                <motion.p
                    className="text-lg text-muted-foreground max-w-2xl mx-auto"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    Verify AI-generated documents. Catch hallucinations. Prove
                    comprehension. Ship with confidence.
                </motion.p>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                <button
                    onClick={handleCreate}
                    disabled={creating}
                    className="glass-card w-full flex items-center gap-4 hover:border-primary/50 transition-all cursor-pointer group text-left"
                >
                    <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center group-hover:bg-primary/30 transition-colors">
                        {creating ? <Loader2 className="w-6 h-6 text-primary animate-spin" /> : <Plus className="w-6 h-6 text-primary" />}
                    </div>
                    <div>
                        <h3 className="font-semibold text-foreground">
                            New Verification Project
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            Upload or generate a document to verify
                        </p>
                    </div>
                </button>
            </motion.div>

            <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                    <FolderOpen className="w-5 h-5" />
                    Recent Projects
                </h2>
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                ) : projects.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">
                        No projects yet. Create one above to get started.
                    </p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {projects.map((project: any, i: number) => (
                            <motion.div
                                key={project.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 + i * 0.1 }}
                            >
                                <Link
                                    to={`/project/${project.id}/input`}
                                    className="glass-card block hover:border-primary/30 transition-all"
                                >
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <h3 className="font-semibold text-foreground">
                                                {project.name}
                                            </h3>
                                            <div className="flex items-center gap-3 mt-2 text-sm">
                                                <span className={statusColors[project.status] || "text-muted-foreground"}>
                                                    <Shield className="w-3.5 h-3.5 inline mr-1" />
                                                    {project.status}
                                                </span>
                                                <span className="text-muted-foreground flex items-center gap-1">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    {new Date(project.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
