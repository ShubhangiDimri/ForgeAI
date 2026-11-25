import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, PanelRightClose, PanelRightOpen, RotateCcw, Send } from 'lucide-react';
import { api } from '../services/api';
import type { RunDetail, RunSummary } from '../types/forgeai';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  refused?: boolean;
  retrieved?: { id: string; file: string; text: string }[];
  tools?: { name: string; arguments: Record<string, unknown>; results: Record<string, string> }[];
  timestamp: string;
}

export function PlaygroundPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState(searchParams.get('run') || '');
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(true);

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
    api
      .getRun(selectedRun)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load agent'));
  }, [selectedRun]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRun || !input.trim() || sending) return;
    const question = input.trim();
    setInput('');
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
    ]);
    setSending(true);
    try {
      const trace = await api.chat(selectedRun, question);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: trace.answer?.answer || trace.error || 'No response produced.',
          citations: trace.answer?.citations || [],
          refused: trace.answer?.refused ?? false,
          retrieved: trace.retrieved,
          tools: trace.tools,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat request failed');
    } finally {
      setSending(false);
    }
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)]">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#E4E0D8]">
        <div className="flex items-center gap-3">
          <h1 className="font-serif-heading text-xl font-medium text-[#292724]">
            Interactive chat
          </h1>
          <select
            value={selectedRun}
            onChange={(e) => {
              setSelectedRun(e.target.value);
              setSearchParams({ run: e.target.value });
              setMessages([]);
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

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMessages([])}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#E4E0D8] bg-white text-xs text-[#292724] hover:bg-[#F3F1EB]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New conversation
          </button>
          <button
            type="button"
            onClick={() => setShowPanel((v) => !v)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-[#E4E0D8] bg-white text-xs text-[#292724] hover:bg-[#F3F1EB]"
          >
            {showPanel ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
            Grounding
          </button>
        </div>
      </div>

      <div className="flex-1 flex min-h-0 pt-4 gap-6">
        {/* Chat column */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {detail && (
              <div className="pb-3 border-b border-[#E4E0D8]">
                <div className="text-base font-medium text-[#292724]">{detail.id}</div>
                <div className="text-xs text-[#78756F]">{detail.agent_config.requirements.scope}</div>
              </div>
            )}

            {messages.length === 0 && (
              <div className="py-12 text-center text-sm text-[#78756F]">
                Ask a question to test the selected agent&apos;s grounding, citations, tools, and refusal behavior.
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="flex items-start gap-3">
                <span
                  className={`w-6 h-6 rounded flex items-center justify-center text-xs font-medium shrink-0 mt-0.5 ${
                    msg.role === 'user'
                      ? 'bg-[#EAE5DC] text-[#292724]'
                      : 'bg-[#F5E6DF] text-[#C96442]'
                  }`}
                >
                  {msg.role === 'user' ? 'U' : 'A'}
                </span>
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <div className="text-sm text-[#292724] whitespace-pre-wrap">{msg.content}</div>
                    <span className="text-[11px] text-[#78756F] shrink-0">{msg.timestamp}</span>
                  </div>

                  {msg.refused && (
                    <span className="inline-block text-xs px-2 py-0.5 rounded border border-amber-300 bg-amber-50 text-amber-900">
                      Refused
                    </span>
                  )}

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-xs text-[#78756F]">
                      <span>Sources:</span>
                      {msg.citations.map((c) => (
                        <span
                          key={c}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-[#E4E0D8] bg-[#F3F1EB] text-[#292724] font-mono text-[11px]"
                        >
                          <FileText className="w-3 h-3" />
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  {msg.tools && msg.tools.length > 0 && (
                    <div className="p-2.5 rounded border border-[#E4E0D8] bg-[#FAF9F5] text-xs space-y-1">
                      <div className="font-medium text-[#292724]">Tool calls</div>
                      {msg.tools.map((t, ti) => (
                        <div key={ti} className="font-mono text-[11px] text-[#78756F]">
                          {t.name}({JSON.stringify(t.arguments)}) → {JSON.stringify(t.results)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-2 p-2.5 rounded border border-red-200 bg-red-50 text-xs text-red-800">
              {error}
            </div>
          )}

          <form onSubmit={handleSend} className="pt-3 mt-2 border-t border-[#E4E0D8] flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 px-3 py-2 rounded-md border border-[#E4E0D8] bg-white text-sm text-[#292724] focus:outline-none focus:border-[#C96442]"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#C96442] text-white text-sm font-medium hover:bg-[#b55737] disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {sending ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>

        {/* Right Grounding & Config panel */}
        {showPanel && detail && (
          <aside className="w-72 shrink-0 border-l border-[#E4E0D8] pl-5 overflow-y-auto space-y-5 hidden md:block">
            <div>
              <h2 className="text-sm font-medium text-[#292724] mb-2">Grounding</h2>
              <div className="p-3 rounded-md border border-[#E4E0D8] bg-white text-xs space-y-1">
                <div className="font-medium text-[#292724]">
                  {Object.keys(detail.document_manifest || {}).length} documents
                </div>
                <div className="text-[#78756F] font-mono break-all">{detail.agent_config.model}</div>
              </div>
            </div>

            {lastAssistant?.retrieved && lastAssistant.retrieved.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-[#292724] mb-2">
                  Retrieved sources ({lastAssistant.retrieved.length})
                </h2>
                <div className="space-y-2">
                  {lastAssistant.retrieved.map((p) => (
                    <div
                      key={p.id}
                      className="p-2.5 rounded-md border border-[#E4E0D8] bg-white text-xs space-y-1"
                    >
                      <div className="font-mono text-[11px] font-medium text-[#292724]">{p.id}</div>
                      <div className="text-[#78756F] line-clamp-3">{p.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h2 className="text-sm font-medium text-[#292724] mb-2">Configuration</h2>
              <div className="p-3 rounded-md border border-[#E4E0D8] bg-white text-xs space-y-2">
                <div>
                  <span className="text-[#78756F]">Retrieval: </span>
                  <span className="font-mono">
                    top_k={detail.agent_config.settings.top_k}, min_score=
                    {detail.agent_config.settings.min_score}
                  </span>
                </div>
                <div>
                  <span className="text-[#78756F]">Tools: </span>
                  <span>
                    {detail.agent_config.tools.length > 0
                      ? detail.agent_config.tools.map((t) => t.name).join(', ')
                      : 'None'}
                  </span>
                </div>
                <div>
                  <div className="text-[#78756F] mb-0.5">System prompt</div>
                  <div className="text-[#292724] leading-relaxed">
                    {detail.agent_config.system_prompt}
                  </div>
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

