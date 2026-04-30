/** @type {import('tailwindcss').Config} */
export default {
    darkMode: "class",
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                card: "hsl(var(--card))",
                "card-foreground": "hsl(var(--card-foreground))",
                primary: "hsl(var(--primary))",
                "primary-foreground": "hsl(var(--primary-foreground))",
                secondary: "hsl(var(--secondary))",
                "secondary-foreground": "hsl(var(--secondary-foreground))",
                muted: "hsl(var(--muted))",
                "muted-foreground": "hsl(var(--muted-foreground))",
                accent: "hsl(var(--accent))",
                "accent-foreground": "hsl(var(--accent-foreground))",
                destructive: "hsl(var(--destructive))",
                border: "hsl(var(--border))",
                ring: "hsl(var(--ring))",
                verified: "#22c55e",
                uncertain: "#eab308",
                hallucinated: "#ef4444",
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            animation: {
                "pulse-glow": "pulse-glow 2s ease-in-out infinite",
                "score-fill": "score-fill 1.5s ease-out forwards",
            },
            keyframes: {
                "pulse-glow": {
                    "0%, 100%": { opacity: "0.6" },
                    "50%": { opacity: "1" },
                },
                "score-fill": {
                    from: { "stroke-dashoffset": "283" },
                    to: { "stroke-dashoffset": "var(--score-offset)" },
                },
            },
        },
    },
    plugins: [],
};
