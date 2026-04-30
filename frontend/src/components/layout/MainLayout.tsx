import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
    FileText,
    Shield,
    HelpCircle,
    BarChart3,
    Home,
} from "lucide-react";

const navItems = [
    { path: "/", label: "Dashboard", icon: Home },
];

const steps = [
    { label: "Input", icon: FileText, step: "input" },
    { label: "Verify", icon: Shield, step: "verify" },
    { label: "Quiz", icon: HelpCircle, step: "quiz" },
    { label: "Report", icon: BarChart3, step: "report" },
];

export function MainLayout({ children }: { children: ReactNode }) {
    const location = useLocation();

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="glass border-b border-white/10 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <Shield className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-xl font-bold gradient-text">
                            GenDoc Confirm
                        </span>
                    </Link>

                    {/* Step indicators (shown on project pages) */}
                    {location.pathname.includes("/project/") && (
                        <div className="flex items-center gap-1">
                            {steps.map((step, i) => {
                                const isActive = location.pathname.includes(step.step);
                                return (
                                    <div key={step.step} className="flex items-center">
                                        <div
                                            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-all ${isActive
                                                ? "bg-primary/20 text-primary"
                                                : "text-muted-foreground"
                                                }`}
                                        >
                                            <step.icon className="w-4 h-4" />
                                            <span className="hidden sm:inline">{step.label}</span>
                                        </div>
                                        {i < steps.length - 1 && (
                                            <div className="w-8 h-px bg-border mx-1" />
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-6 py-8">
                <motion.div
                    key={location.pathname}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                >
                    {children}
                </motion.div>
            </main>
        </div>
    );
}
