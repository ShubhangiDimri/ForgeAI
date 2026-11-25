import type { BuildState, ProvidersResponse, RunDetail, RunSummary } from '../types/forgeai';

const BASE = import.meta.env.VITE_API_BASE_URL || '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; timestamp: string }>('/api/health'),
  providers: () => request<ProvidersResponse>('/api/providers'),
  examples: () =>
    request<{ briefs: { id: string; label: string; brief: string }[]; datasets: { id: string; files: string[] }[] }>(
      '/api/examples'
    ),
  listRuns: () => request<{ runs: RunSummary[] }>('/api/runs'),
  getRun: (runId: string) => request<RunDetail>(`/api/runs/${encodeURIComponent(runId)}`),
  chat: (runId: string, question: string) =>
    request<RunDetail['case_results']['v0'][0]['execution']>(`/api/runs/${encodeURIComponent(runId)}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
  uploadDocuments: async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    return request<{ upload_id: string; files: { name: string; size: number }[] }>('/api/uploads', {
      method: 'POST',
      body: form,
    });
  },
  startBuild: (payload: {
    name: string;
    brief: string;
    upload_id?: string;
    demo_dataset?: string;
    model: string;
    max_iterations: number;
    interactive: boolean;
    prototype_only: boolean;
  }) =>
    request<{ build_id: string; run_id: string; status: string }>('/api/builds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  getBuild: (buildId: string) => request<BuildState>(`/api/builds/${encodeURIComponent(buildId)}`),
  submitIntake: (buildId: string, answers: string[]) =>
    request<{ status: string }>(`/api/builds/${encodeURIComponent(buildId)}/intake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    }),
  approveRequirements: (buildId: string, requirements: NonNullable<BuildState['requirements']>) =>
    request<{ status: string }>(`/api/builds/${encodeURIComponent(buildId)}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requirements }),
    }),
  resumeRun: (runId: string, mode: 'scoring' | 'generation' = 'scoring') =>
    request<{ run_id: string; status: string }>(`/api/runs/${encodeURIComponent(runId)}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    }),
  artifactUrl: (runId: string, filename: string) =>
    `${BASE}/api/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(filename)}`,
  zipUrl: (runId: string) => `${BASE}/api/runs/${encodeURIComponent(runId)}/download-zip`,
};

