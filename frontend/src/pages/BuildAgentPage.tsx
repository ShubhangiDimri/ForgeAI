import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Loader2, Upload, X, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import type { BuildState, ProviderInfo } from '../types/forgeai';

export function BuildAgentPage() {
  const [name, setName] = useState('');
  const [brief, setBrief] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [demoDataset, setDemoDataset] = useState('');
  const [model, setModel] = useState('groq:openai/gpt-oss-120b');
  const [maxIterations, setMaxIterations] = useState(1);
  const [interactive, setInteractive] = useState(false);
  const [prototypeOnly, setPrototypeOnly] = useState(false);

  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [examples, setExamples] = useState<{
    briefs: { id: string; label: string; brief: string }[];
    datasets: { id: string; files: string[] }[];
  }>({ briefs: [], datasets: [] });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [build, setBuild] = useState<BuildState | null>(null);

  // Interactive checkpoint states
  const [answers, setAnswers] = useState<string[]>([]);
  const [editedScope, setEditedScope] = useState('');
  const [editedMustAnswer, setEditedMustAnswer] = useState('');
  const [editedMustRefuse, setEditedMustRefuse] = useState('');

  useEffect(() => {
    api.providers().then((res) => setProviders(res.providers)).catch(() => {});
    api.examples().then(setExamples).catch(() => {});
  }, []);

  // Poll build progress
  useEffect(() => {
    if (!build || build.status === 'completed' || build.status === 'failed') return;
    const timer = setInterval(() => {
      api
        .getBuild(build.build_id)
        .then((next) => {
          setBuild(next);
          if (next.status === 'waiting_intake' && answers.length !== next.questions.length) {
            setAnswers(next.questions.map(() => ''));
          }
          if (next.status === 'waiting_approval' && next.requirements && !editedScope) {
            setEditedScope(next.requirements.scope);
            setEditedMustAnswer(next.requirements.must_answer.join('\n'));
            setEditedMustRefuse(next.requirements.must_refuse.join('\n'));
          }
        })
        .catch(() => {});
    }, 1500);
    return () => clearInterval(timer);
  }, [build, answers.length, editedScope]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const picked = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...picked]);
    setDemoDataset('');
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (brief.trim().length < 10) {
      setError('Please provide a requester brief of at least 10 characters.');
      return;
    }
    if (files.length === 0 && !demoDataset) {
      setError('Please upload at least one PDF, TXT, or CSV file, or select a demo dataset.');
      return;
    }

    setSubmitting(true);
    try {
      let uploadId: string | undefined;
      if (files.length > 0) {
        const up = await api.uploadDocuments(files);
        uploadId = up.upload_id;
      }
      const res = await api.startBuild({
        name: name.trim(),
        brief: brief.trim(),
        upload_id: uploadId,
        demo_dataset: demoDataset || undefined,
        model,
        max_iterations: maxIterations,
        interactive,
        prototype_only: prototypeOnly,
      });
      const initial = await api.getBuild(res.build_id);
      setBuild(initial);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start build');
    } finally {
      setSubmitting(false);
    }
  };

  const handleIntakeSubmit = async () => {
    if (!build) return;
    await api.submitIntake(build.build_id, answers);
  };

  const handleApprove = async () => {
    if (!build || !build.requirements) return;
    await api.approveRequirements(build.build_id, {
      ...build.requirements,
      scope: editedScope.trim() || build.requirements.scope,
      must_answer: editedMustAnswer
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
      must_refuse: editedMustRefuse
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
    });
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <div className="text-xs text-[#78756F] mb-1">Agents / New</div>
        <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">
          Create an agent
        </h1>
        <p className="text-sm text-[#78756F] mt-1">
          Define the task, provide a knowledge source, and let ForgeAI build a grounded, evaluated agent.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-3.5 rounded-md border border-red-200 bg-red-50 text-sm text-red-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[#292724] mb-1.5">
              Agent name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. hr-policy-assistant"
              className="w-full px-3 py-2 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724] focus:outline-none focus:border-[#C96442]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#292724] mb-1.5">
              Provider & model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724] focus:outline-none focus:border-[#C96442]"
            >
              {providers.flatMap((p) =>
                p.models.map((m) => (
                  <option key={m} value={m}>
                    {p.name} — {m}
                  </option>
                ))
              )}
              <option value="auto">Automatic fallback chain</option>
            </select>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm font-medium text-[#292724]">
              Requester brief
            </label>
            {examples.briefs.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  const found = examples.briefs.find((b) => b.id === e.target.value);
                  if (found) setBrief(found.brief);
                }}
                className="text-xs px-2 py-1 rounded border border-[#E4E0D8] bg-white text-[#78756F]"
              >
                <option value="">Load example brief...</option>
                {examples.briefs.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            )}
          </div>
          <textarea
            rows={4}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Describe the agent's scope, audience, tone, must-answer topics, and must-refuse topics..."
            className="w-full px-3 py-2.5 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724] focus:outline-none focus:border-[#C96442]"
          />
          <div className="text-right text-xs text-[#78756F] mt-1">{brief.length} / 4000</div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[#292724] mb-1.5">
              Upload documents (PDF, TXT, CSV)
            </label>
            <label className="flex items-center justify-center gap-2 px-4 py-3 rounded-md border border-dashed border-[#E4E0D8] bg-white text-sm text-[#78756F] hover:border-[#C96442] cursor-pointer">
              <Upload className="w-4 h-4" />
              <span>Select files</span>
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.csv"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
            {files.length > 0 && (
              <ul className="mt-2 space-y-1">
                {files.map((f, i) => (
                  <li
                    key={`${f.name}-${i}`}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded border border-[#E4E0D8] bg-white text-xs"
                  >
                    <span className="truncate">{f.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      className="text-[#78756F] hover:text-red-700"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-[#292724] mb-1.5">
              Or use existing demo dataset
            </label>
            <select
              value={demoDataset}
              onChange={(e) => {
                setDemoDataset(e.target.value);
                if (e.target.value) setFiles([]);
              }}
              className="w-full px-3 py-2.5 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724] focus:outline-none focus:border-[#C96442]"
            >
              <option value="">None (use uploaded files)</option>
              {examples.datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  demo_data/{d.id} ({d.files.length} files)
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#E4E0D8]">
          <div className="flex flex-wrap items-center gap-6 text-sm">
            <label className="flex items-center gap-2">
              <span className="text-[#78756F]">Max iterations</span>
              <select
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                className="px-2 py-1 rounded border border-[#E4E0D8] bg-white text-sm"
              >
                {[0, 1, 2, 3].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={interactive}
                onChange={(e) => setInteractive(e.target.checked)}
                className="accent-[#C96442]"
              />
              <span>Interactive intake & review</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prototypeOnly}
                onChange={(e) => setPrototypeOnly(e.target.checked)}
                className="accent-[#C96442]"
              />
              <span>Prototype only</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting || build?.status === 'running'}
            className="px-5 py-2 rounded-md bg-[#C96442] text-white text-sm font-medium hover:bg-[#b55737] disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Starting...' : 'Build agent ->'}
          </button>
        </div>
      </form>

      {/* Interactive Intake Checkpoint */}
      {build?.status === 'waiting_intake' && (
        <div className="p-5 rounded-md border border-[#C96442] bg-white space-y-4">
          <h2 className="font-serif-heading text-lg font-medium text-[#292724]">
            Clarification questions
          </h2>
          <p className="text-xs text-[#78756F]">
            Answer up to {build.questions.length} questions (leave blank to record as unresolved).
          </p>
          <div className="space-y-3">
            {build.questions.map((q, idx) => (
              <div key={idx}>
                <label className="block text-sm font-medium text-[#292724] mb-1">{q}</label>
                <input
                  type="text"
                  value={answers[idx] || ''}
                  onChange={(e) => {
                    const next = [...answers];
                    next[idx] = e.target.value;
                    setAnswers(next);
                  }}
                  className="w-full px-3 py-1.5 rounded border border-[#E4E0D8] text-sm"
                />
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={handleIntakeSubmit}
            className="px-4 py-2 rounded-md bg-[#C96442] text-white text-sm font-medium"
          >
            Submit answers
          </button>
        </div>
      )}

      {/* Interactive Requirements Approval Checkpoint */}
      {build?.status === 'waiting_approval' && build.requirements && (
        <div className="p-5 rounded-md border border-[#C96442] bg-white space-y-4">
          <h2 className="font-serif-heading text-lg font-medium text-[#292724]">
            Review requirements & groundability
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <label className="block font-medium mb-1">Scope</label>
              <input
                type="text"
                value={editedScope}
                onChange={(e) => setEditedScope(e.target.value)}
                className="w-full px-3 py-1.5 rounded border border-[#E4E0D8]"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block font-medium mb-1">Must-answer topics (one per line)</label>
                <textarea
                  rows={4}
                  value={editedMustAnswer}
                  onChange={(e) => setEditedMustAnswer(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[#E4E0D8]"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Must-refuse topics (one per line)</label>
                <textarea
                  rows={4}
                  value={editedMustRefuse}
                  onChange={(e) => setEditedMustRefuse(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-[#E4E0D8]"
                />
              </div>
            </div>
            {build.coverage && (
              <div className="pt-2">
                <div className="font-medium mb-1.5">Groundability findings</div>
                <div className="space-y-1.5">
                  {Object.entries(build.coverage).map(([topic, f]) => (
                    <div
                      key={topic}
                      className="flex items-center justify-between px-3 py-1.5 rounded bg-[#FAF9F5] border border-[#E4E0D8] text-xs"
                    >
                      <span className="font-medium">{topic}</span>
                      <span className="text-[#78756F]">{f.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={handleApprove}
            className="px-4 py-2 rounded-md bg-[#C96442] text-white text-sm font-medium"
          >
            Approve & continue
          </button>
        </div>
      )}

      {/* Execution Pipeline */}
      {build && (
        <div className="pt-4 border-t border-[#E4E0D8] space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-serif-heading text-lg font-medium text-[#292724]">
                Execution pipeline
              </h2>
              <p className="text-xs text-[#78756F]">
                Run ID: <span className="font-mono">{build.run_id}</span> · Model:{' '}
                <span className="font-mono">{build.model}</span>
                {build.elapsed_seconds > 0 ? ` · ${build.elapsed_seconds}s` : ''}
              </p>
            </div>
            {build.status === 'completed' && (
              <Link
                to={`/playground?run=${encodeURIComponent(build.run_id)}`}
                className="px-3 py-1.5 rounded border border-[#E4E0D8] bg-white text-xs font-medium hover:bg-[#F3F1EB]"
              >
                Open in Playground
              </Link>
            )}
          </div>

          {build.error && (
            <div className="p-3 rounded border border-red-200 bg-red-50 text-xs text-red-800">
              {build.error}
            </div>
          )}

          <div className="rounded-md border border-[#E4E0D8] bg-white divide-y divide-[#E4E0D8]">
            {build.stages.map((stage, idx) => (
              <div key={stage.name} className="px-4 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-6 h-6 rounded-full border border-[#E4E0D8] bg-[#FAF9F5] flex items-center justify-center text-xs text-[#78756F] shrink-0">
                    {stage.status === 'completed' ? (
                      <Check className="w-3.5 h-3.5 text-emerald-700" />
                    ) : stage.status === 'running' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-[#C96442]" />
                    ) : (
                      String(idx + 1).padStart(2, '0')
                    )}
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-[#292724]">{stage.name}</div>
                    {stage.detail && (
                      <div className="text-xs text-[#78756F] truncate">{stage.detail}</div>
                    )}
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded border border-[#E4E0D8] bg-[#FAF9F5] text-[#78756F] capitalize shrink-0">
                  {stage.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

