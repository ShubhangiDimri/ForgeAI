export interface ProviderInfo {
  id: string;
  name: string;
  configured: boolean;
  default_model: string;
  judge_model?: string;
  models: string[];
}

export interface ProvidersResponse {
  providers: ProviderInfo[];
  fallback_order: string[];
  default_embedding: string;
}

export interface RunSummary {
  id: string;
  scope: string;
  model: string;
  status: string;
  created_at: string;
  finished_at?: string | null;
  selected_version?: number | null;
  baseline_pass_rate?: number | null;
  selected_pass_rate?: number | null;
  total_cases?: number | null;
  tools: string[];
}

export interface Scorecard {
  version: number;
  total: number;
  passed: number;
  failed: number;
  error: number;
  pass_rate: number;
  dimensions: Record<string, { passed: number; scored: number }>;
  seconds: number;
}

export interface IterationLog {
  iteration: number;
  base_version: number;
  changes: Record<string, { before: unknown; after: unknown }>;
  reason: string;
  affected_case_ids: string[];
  before: Scorecard;
  after?: Scorecard;
  outcome?: string;
}

export interface EvalCase {
  id: string;
  question: string;
  category: string;
  expected_refusal: boolean;
  expected_facts: { source_id: string; document: string; fact: string }[];
  expected_tools: string[];
}

export interface CaseResult {
  case: EvalCase;
  execution: {
    answer: { answer: string; citations: string[]; refused: boolean } | null;
    retrieved: { id: string; file: string; text: string; page?: number | null; row?: number | null }[];
    tools: { name: string; arguments: Record<string, unknown>; results: Record<string, string> }[];
    error?: string | null;
    invalid_citation: boolean;
    invalid_tool_call: boolean;
    refusal_code?: string | null;
  };
  judgment?: {
    correct: boolean;
    grounded: boolean;
    citations_relevant: boolean;
    refusal_appropriate: boolean;
    tools_correct: boolean;
    explanation: string;
  } | null;
  status: 'passed' | 'failed' | 'error';
  failure?: string | null;
  explanation: string;
}

export interface RunDetail {
  id: string;
  agent_config: {
    system_prompt: string;
    settings: { chunk_words: number; overlap: number; top_k: number; min_score: number };
    tools: { name: string; reason: string }[];
    model: string;
    embedding: string;
    requirements: {
      scope: string;
      audience: string;
      tone: string;
      must_answer: string[];
      must_refuse: string[];
      assumptions: string[];
      unresolved: string[];
    };
    coverage: Record<string, { status: string; evidence: { id: string; quote: string }[]; limitation: string }>;
    output_contract: Record<string, unknown>;
  };
  requirements: RunDetail['agent_config']['requirements'] | null;
  coverage: RunDetail['agent_config']['coverage'] | null;
  document_manifest: Record<string, string> | null;
  run_metadata: Record<string, unknown> | null;
  eval_dataset: { cases: EvalCase[] } | null;
  scorecards: Scorecard[];
  iteration_logs: IterationLog[];
  case_results: Record<string, CaseResult[]>;
  final_report: string | null;
  files: { name: string; size: number }[];
}

export interface BuildStage {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  detail: string;
}

export interface BuildState {
  build_id: string;
  run_id: string;
  status: 'running' | 'waiting_intake' | 'waiting_approval' | 'completed' | 'failed';
  current_stage: string;
  model: string;
  stages: BuildStage[];
  questions: string[];
  requirements: RunDetail['agent_config']['requirements'] | null;
  coverage: RunDetail['agent_config']['coverage'] | null;
  error: string | null;
  elapsed_seconds: number;
}

