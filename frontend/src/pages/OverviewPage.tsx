import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BarChart3, FileText, MessageSquare, Plus } from 'lucide-react';
import { api } from '../services/api';
import type { RunSummary } from '../types/forgeai';

export function OverviewPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listRuns()
      .then((res) => setRuns(res.runs))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load runs'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">
            Your workspace
          </h1>
          <p className="text-sm text-[#78756F] mt-1">
            Generated agents, evaluation scorecards, and demonstration artifacts.
          </p>
        </div>
        <Link
          to="/build"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[#C96442] text-white text-sm font-medium hover:bg-[#b55737] transition-colors"
        >
          <Plus className="w-4 h-4" />
          Build new agent
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-md border border-red-200 bg-red-50 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-8 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#78756F]">
          Loading workspace artifacts...
        </div>
      ) : runs.length === 0 ? (
        <div className="p-10 rounded-md border border-[#E4E0D8] bg-white text-center space-y-3">
          <p className="text-sm font-medium text-[#292724]">No generated agents found</p>
          <p className="text-sm text-[#78756F]">
            Upload documents and provide a requester brief to build your first grounded agent.
          </p>
          <Link
            to="/build"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[#C96442] hover:underline"
          >
            Build new agent <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="rounded-md border border-[#E4E0D8] bg-white overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#E4E0D8] bg-[#FAF9F5] text-xs font-medium text-[#78756F]">
                <th className="py-2.5 px-4">Agent / Run</th>
                <th className="py-2.5 px-4">Model</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Score</th>
                <th className="py-2.5 px-4">Created</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E0D8] text-sm">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-[#FAF9F5]/70">
                  <td className="py-3 px-4">
                    <div className="font-medium text-[#292724]">{run.id}</div>
                    <div className="text-xs text-[#78756F] line-clamp-1 max-w-xs">{run.scope}</div>
                  </td>
                  <td className="py-3 px-4 text-xs text-[#78756F] font-mono">{run.model}</td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center px-2 py-0.5 rounded border border-[#E4E0D8] bg-[#FAF9F5] text-xs text-[#292724]">
                      {run.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-[#292724]">
                    {run.selected_pass_rate !== null && run.selected_pass_rate !== undefined
                      ? `${Math.round(run.selected_pass_rate * 100)}% (${run.total_cases ?? 20} cases)`
                      : '—'}
                  </td>
                  <td className="py-3 px-4 text-xs text-[#78756F]">
                    {new Date(run.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      <Link
                        to={`/playground?run=${encodeURIComponent(run.id)}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-[#E4E0D8] text-xs text-[#292724] hover:bg-[#F3F1EB]"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Playground
                      </Link>
                      <Link
                        to={`/evaluations?run=${encodeURIComponent(run.id)}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-[#E4E0D8] text-xs text-[#292724] hover:bg-[#F3F1EB]"
                      >
                        <BarChart3 className="w-3.5 h-3.5" />
                        Eval
                      </Link>
                      <Link
                        to={`/reports?run=${encodeURIComponent(run.id)}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-[#E4E0D8] text-xs text-[#292724] hover:bg-[#F3F1EB]"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        Reports
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

