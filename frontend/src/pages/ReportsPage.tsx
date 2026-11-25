import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Download, FileArchive } from 'lucide-react';
import { api } from '../services/api';
import type { RunDetail, RunSummary } from '../types/forgeai';

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState(searchParams.get('run') || '');
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [previewKey, setPreviewKey] = useState<'final_report' | 'agent_config' | 'requirements' | 'coverage' | 'scorecards'>('final_report');

  useEffect(() => {
    api.listRuns().then((res) => {
      setRuns(res.runs);
      if (!selectedRun && res.runs.length > 0) {
        const first = res.runs[0].id;
        setSelectedRun(first);
        setSearchParams({ run: first });
      }
    });
  }, [selectedRun, setSearchParams]);

  useEffect(() => {
    if (!selectedRun) return;
    api.getRun(selectedRun).then(setDetail);
  }, [selectedRun]);

  const previewContent = () => {
    if (!detail) return '';
    if (previewKey === 'final_report') return detail.final_report || 'No final_report.md generated.';
    if (previewKey === 'agent_config') return JSON.stringify(detail.agent_config, null, 2);
    if (previewKey === 'requirements') return JSON.stringify(detail.requirements, null, 2);
    if (previewKey === 'coverage') return JSON.stringify(detail.coverage, null, 2);
    return JSON.stringify(detail.scorecards, null, 2);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">Reports</h1>
          <p className="text-sm text-[#78756F] mt-1">
            Inspect and download generated definitions, scorecards, and quality reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedRun}
            onChange={(e) => {
              setSelectedRun(e.target.value);
              setSearchParams({ run: e.target.value });
            }}
            className="px-3 py-1.5 rounded-md border border-[#E4E0D8] bg-white text-sm"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id}
              </option>
            ))}
          </select>

          {selectedRun && (
            <a
              href={api.zipUrl(selectedRun)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#C96442] text-white text-xs font-medium hover:bg-[#b55737]"
            >
              <FileArchive className="w-3.5 h-3.5" />
              Download ZIP
            </a>
          )}
        </div>
      </div>

      {detail && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="space-y-4">
            <div className="rounded-md border border-[#E4E0D8] bg-white p-3 space-y-1">
              <div className="text-xs font-medium text-[#78756F] px-2 pb-1">Preview</div>
              {[
                { id: 'final_report', label: 'Final quality report' },
                { id: 'agent_config', label: 'Agent definition' },
                { id: 'requirements', label: 'Requirements' },
                { id: 'coverage', label: 'Groundability' },
                { id: 'scorecards', label: 'Scorecards' },
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setPreviewKey(item.id as typeof previewKey)}
                  className={`w-full text-left px-2.5 py-1.5 rounded text-xs ${
                    previewKey === item.id
                      ? 'bg-[#EAE5DC] text-[#292724] font-medium'
                      : 'text-[#78756F] hover:bg-[#FAF9F5]'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="rounded-md border border-[#E4E0D8] bg-white p-3 space-y-1">
              <div className="text-xs font-medium text-[#78756F] px-2 pb-1">Files</div>
              {detail.files.map((f) => (
                <a
                  key={f.name}
                  href={api.artifactUrl(detail.id, f.name)}
                  download={f.name}
                  className="flex items-center justify-between px-2 py-1 rounded text-xs text-[#292724] hover:bg-[#FAF9F5]"
                >
                  <span className="truncate font-mono">{f.name}</span>
                  <Download className="w-3 h-3 text-[#78756F] shrink-0" />
                </a>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3 rounded-md border border-[#E4E0D8] bg-white p-5 overflow-x-auto">
            <pre className="text-xs font-mono text-[#292724] whitespace-pre-wrap leading-relaxed">
              {previewContent()}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

