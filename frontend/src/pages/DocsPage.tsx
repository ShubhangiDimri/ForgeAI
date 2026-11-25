export function DocsPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">Documentation</h1>
        <p className="text-sm text-[#78756F] mt-1">
          Architecture, CLI commands, and local development workflow.
        </p>
      </div>

      <div className="p-5 rounded-md border border-[#E4E0D8] bg-white space-y-4 text-sm">
        <div>
          <h2 className="font-medium text-[#292724] mb-1">Backend API</h2>
          <pre className="p-3 rounded bg-[#FAF9F5] border border-[#E4E0D8] text-xs font-mono overflow-x-auto">
            cd backend{'\n'}python -m uvicorn api.main:app --reload --port 8000
          </pre>
        </div>

        <div>
          <h2 className="font-medium text-[#292724] mb-1">Frontend Dev</h2>
          <pre className="p-3 rounded bg-[#FAF9F5] border border-[#E4E0D8] text-xs font-mono overflow-x-auto">
            cd frontend{'\n'}npm install{'\n'}npm run dev
          </pre>
        </div>

        <div>
          <h2 className="font-medium text-[#292724] mb-1">CLI Commands</h2>
          <pre className="p-3 rounded bg-[#FAF9F5] border border-[#E4E0D8] text-xs font-mono overflow-x-auto">
            cd backend{'\n'}
            python -m pytest -q{'\n'}
            python -m forgeai chat --config .\artifacts\groq-academic-final\agent_config.json{'\n'}
            python -m forgeai evaluate --resume-scoring --run .\artifacts\groq-academic-final
          </pre>
        </div>
      </div>
    </div>
  );
}

