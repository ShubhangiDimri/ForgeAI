import { Fragment, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../services/api';
import type { CaseResult, RunDetail, RunSummary } from '../types/forgeai';

export function EvaluationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState(searchParams.get('run') || '');
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'cases' | 'metrics' | 'optimization'>('cases');
  const [versionKey, setVersionKey] = useState('v0');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.listRuns().then((res) => {
      setRuns(res.runs);
      if (!selectedRun && res.runs.length > 0) {
        const preferred = res.runs.find((r) => r.id === 'groq-academic-final') || res.runs[0];
        setSelectedRun(preferred.id);
        setSearchParams({ run: preferred.id });
      }
    });
  }, [selectedRun, setSearchParams]);

  useEffect(() => {
    if (!selectedRun) return;
    api.getRun(selectedRun).then((d) => {
      setDetail(d);
      const keys = Object.keys(d.case_results);
      if (keys.length > 0) setVersionKey(keys[0]);
    });
  }, [selectedRun]);

  const results: CaseResult[] = detail?.case_results[versionKey] || [];
  const filtered = results.filter((r) => {
    if (categoryFilter !== 'all' && r.case.category !== categoryFilter) return false;
    if (statusFilter !== 'all' && r.status !== statusFilter) return false;
    return true;
  });

  const selectedVersion =
    typeof detail?.run_metadata?.selected_version === 'number'
      ? detail.run_metadata.selected_version
      : 0;
  const selectedCard = detail?.scorecards[selectedVersion] || detail?.scorecards[0];

  const chartData = (detail?.scorecards || []).map((c) => ({
    name: `v${c.version}`,
    passed: c.passed,
    failed: c.failed,
    error: c.error,
    rate: Math.round(c.pass_rate * 100),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs text-[#78756F] mb-1">Evaluations / {selectedRun || 'Select run'}</div>
          <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">
            Agent evaluation
          </h1>
          <p className="text-sm text-[#78756F] mt-1">
            Automated tests to verify accuracy, grounding, and refusal adherence.
          </p>
        </div>

        <select
          value={selectedRun}
          onChange={(e) => {
            setSelectedRun(e.target.value);
            setSearchParams({ run: e.target.value });
            setExpanded(null);
          }}
          className="px-3 py-1.5 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724]"
        >
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id}
            </option>
          ))}
        </select>
      </div>

      {selectedCard && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-md border border-[#E4E0D8] bg-white flex items-center justify-between">
            <div>
              <div className="text-xs text-[#78756F]">
                Selected version (v{selectedCard.version})
              </div>
              <div className="text-xl font-medium text-[#292724] mt-1">
                {selectedCard.passed} / {selectedCard.total} tests passed
              </div>
              <div className="text-xs text-[#78756F] mt-0.5">
                {selectedCard.failed} failed · {selectedCard.error} infrastructure error
              </div>
            </div>
            <span className="px-2.5 py-1 rounded bg-[#F5E6DF] text-[#C96442] text-sm font-medium">
              {Math.round(selectedCard.pass_rate * 100)}%
            </span>
          </div>

          <div className="p-4 rounded-md border border-[#E4E0D8] bg-white">
            <div className="text-xs text-[#78756F]">Grounding</div>
            <div className="text-xl font-medium text-[#292724] mt-1">
              {selectedCard.dimensions.grounded
                ? `${Math.round(
                    (selectedCard.dimensions.grounded.passed /
                      Math.max(1, selectedCard.dimensions.grounded.scored)) *
                      100
                  )}% grounded`
                : '—'}
            </div>
            <div className="text-xs text-[#78756F] mt-0.5">
              {selectedCard.dimensions.grounded
                ? `${selectedCard.dimensions.grounded.passed}/${selectedCard.dimensions.grounded.scored} scored cases`
                : ''}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-[#E4E0D8] flex gap-6 text-sm">
        {[
          { id: 'cases', label: 'Test cases' },
          { id: 'metrics', label: 'Metrics' },
          { id: 'optimization', label: 'Optimization log' },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id as typeof activeTab)}
            className={`pb-2.5 border-b-2 transition-colors ${
              activeTab === t.id
                ? 'border-[#C96442] text-[#292724] font-medium'
                : 'border-transparent text-[#78756F] hover:text-[#292724]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'cases' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <select
              value={versionKey}
              onChange={(e) => setVersionKey(e.target.value)}
              className="px-2.5 py-1.5 rounded border border-[#E4E0D8] bg-white"
            >
              {Object.keys(detail?.case_results || {}).map((k) => (
                <option key={k} value={k}>
                  Version {k.replace('v', '')}
                </option>
              ))}
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded border border-[#E4E0D8] bg-white"
            >
              <option value="all">All categories</option>
              <option value="direct">direct</option>
              <option value="out_of_scope">out_of_scope</option>
              <option value="unsupported">unsupported</option>
              <option value="ambiguous">ambiguous</option>
              <option value="multi_document">multi_document</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded border border-[#E4E0D8] bg-white"
            >
              <option value="all">All statuses</option>
              <option value="passed">passed</option>
              <option value="failed">failed</option>
              <option value="error">error</option>
            </select>
          </div>

          <div className="rounded-md border border-[#E4E0D8] bg-white overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-[#E4E0D8] bg-[#FAF9F5] text-xs font-medium text-[#78756F]">
                  <th className="py-2.5 px-3 w-8" />
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Test case</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Result</th>
                  <th className="py-2.5 px-3">Grounding</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E0D8]">
                {filtered.map((r) => {
                  const isOpen = expanded === r.case.id;
                  return (
                    <Fragment key={r.case.id}>
                      <tr
                        className="hover:bg-[#FAF9F5] cursor-pointer"
                        onClick={() => setExpanded(isOpen ? null : r.case.id)}
                      >
                        <td className="py-2.5 px-3 text-[#78756F]">
                          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-xs text-[#78756F]">{r.case.id}</td>
                        <td className="py-2.5 px-3 text-[#292724]">{r.case.question}</td>
                        <td className="py-2.5 px-3 text-xs text-[#78756F]">{r.case.category}</td>
                        <td className="py-2.5 px-3 text-xs">
                          <span
                            className={`px-2 py-0.5 rounded border ${
                              r.status === 'passed'
                                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                                : r.status === 'failed'
                                ? 'border-red-200 bg-red-50 text-red-800'
                                : 'border-amber-200 bg-amber-50 text-amber-800'
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-xs text-[#78756F]">
                          {r.judgment?.grounded ? 'Grounded' : r.failure || '—'}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="bg-[#FAF9F5]">
                          <td colSpan={6} className="p-4 text-xs space-y-2">
                            <div>
                              <span className="font-medium text-[#292724]">Answer: </span>
                              <span className="text-[#292724]">
                                {r.execution.answer?.answer || r.execution.error || 'No answer'}
                              </span>
                            </div>
                            <div>
                              <span className="font-medium text-[#292724]">Judge explanation: </span>
                              <span className="text-[#78756F]">{r.explanation}</span>
                            </div>
                            {r.case.expected_facts.length > 0 && (
                              <div>
                                <div className="font-medium text-[#292724] mb-1">Expected facts:</div>
                                <ul className="list-disc pl-4 space-y-0.5 text-[#78756F]">
                                  {r.case.expected_facts.map((f, fi) => (
                                    <li key={fi}>
                                      <span className="font-mono">{f.source_id}</span>: {f.fact}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'metrics' && (
        <div className="p-5 rounded-md border border-[#E4E0D8] bg-white space-y-4">
          <h2 className="text-sm font-medium text-[#292724]">
            Baseline vs optimization iterations
          </h2>
          {chartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="name" stroke="#78756F" fontSize={12} />
                  <YAxis stroke="#78756F" fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="passed" fill="#C96442" name="Passed" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="failed" fill="#D6D1C7" name="Failed" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-sm text-[#78756F]">No scorecards recorded for this run.</div>
          )}
        </div>
      )}

      {activeTab === 'optimization' && (
        <div className="space-y-4">
          {detail?.iteration_logs && detail.iteration_logs.length > 0 ? (
            detail.iteration_logs.map((log) => (
              <div
                key={log.iteration}
                className="p-4 rounded-md border border-[#E4E0D8] bg-white space-y-2 text-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[#292724]">
                    Iteration {log.iteration} (base v{log.base_version})
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded border border-[#E4E0D8] bg-[#FAF9F5]">
                    {log.outcome || 'unmeasured'}
                  </span>
                </div>
                <div className="text-xs text-[#78756F]">{log.reason}</div>
                <div className="text-xs text-[#292724]">
                  Before: {log.before.passed}/{log.before.total} (
                  {Math.round(log.before.pass_rate * 100)}%)
                  {log.after
                    ? ` → After: ${log.after.passed}/${log.after.total} (${Math.round(
                        log.after.pass_rate * 100
                      )}%)`
                    : ''}
                </div>
                <div className="text-xs text-[#78756F]">
                  Affected cases: {log.affected_case_ids.join(', ')}
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#78756F]">
              No optimization iterations recorded.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

