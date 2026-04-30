const API_BASE = "/api/v1";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
}

export const api = {
    projects: {
        list: () => fetchJSON<any[]>("/projects"),
        get: (id: string) => fetchJSON<any>(`/projects/${id}`),
        create: (data: { name: string; description?: string }) =>
            fetchJSON<any>("/projects", {
                method: "POST",
                body: JSON.stringify(data),
            }),
    },

    documents: {
        set: (projectId: string, data: { document?: string; prompt?: string }) =>
            fetchJSON<any>(`/projects/${projectId}/document`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        get: (projectId: string) =>
            fetchJSON<any>(`/projects/${projectId}/document`),
    },

    verification: {
        start: (projectId: string): EventSource => {
            // EventSource only supports GET, but our endpoint is POST.
            // Use a wrapper: send a POST to start, then open GET for results stream.
            // Actually our endpoint returns SSE on POST — use fetch + ReadableStream instead.
            // But for simplicity, let's keep EventSource-compatible: change backend to GET.
            return new EventSource(`${API_BASE}/projects/${projectId}/verify`);
        },
        startFetch: async (projectId: string): Promise<ReadableStream<Uint8Array> | null> => {
            const response = await fetch(`${API_BASE}/projects/${projectId}/verify`, {
                method: "POST",
                headers: { "Accept": "text/event-stream" },
            });
            return response.body;
        },
        results: (projectId: string) =>
            fetchJSON<any>(`/projects/${projectId}/verify/results`),
    },

    quiz: {
        get: (projectId: string) =>
            fetchJSON<any>(`/projects/${projectId}/quiz`),
        submit: (projectId: string, answers: Record<string, string>) =>
            fetchJSON<any>(`/projects/${projectId}/quiz/submit`, {
                method: "POST",
                body: JSON.stringify({ answers }),
            }),
    },

    report: {
        get: (projectId: string) => fetchJSON<any>(`/projects/${projectId}/report`),
    },

    evidence: {
        list: (projectId: string) =>
            fetchJSON<any>(`/projects/${projectId}/evidence`),
        add: (projectId: string, data: { label?: string; content: string }) =>
            fetchJSON<any>(`/projects/${projectId}/evidence`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        remove: (projectId: string, evidenceId: string) =>
            fetchJSON<any>(`/projects/${projectId}/evidence/${evidenceId}`, {
                method: "DELETE",
            }),
    },
};
