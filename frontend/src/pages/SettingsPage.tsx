import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ProvidersResponse } from '../types/forgeai';

export function SettingsPage() {
  const [data, setData] = useState<ProvidersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .providers()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load provider status'));
  }, []);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-serif-heading text-2xl font-medium text-[#292724]">Settings</h1>
        <p className="text-sm text-[#78756F] mt-1">
          Backend provider configuration and fallback order. API credentials remain exclusively on the backend.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded border border-red-200 bg-red-50 text-xs text-red-800">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="rounded-md border border-[#E4E0D8] bg-white divide-y divide-[#E4E0D8]">
            {data.providers.map((p) => (
              <div key={p.id} className="p-4 flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-medium text-[#292724]">{p.name}</div>
                  <div className="text-xs text-[#78756F] font-mono mt-0.5">{p.default_model}</div>
                </div>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded border ${
                    p.configured
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-[#E4E0D8] bg-[#FAF9F5] text-[#78756F]'
                  }`}
                >
                  {p.configured ? 'Configured' : 'Not configured'}
                </span>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-md border border-[#E4E0D8] bg-white text-sm space-y-2">
            <div>
              <span className="text-[#78756F]">Fallback order: </span>
              <span className="font-mono text-xs">{data.fallback_order.join(' → ')}</span>
            </div>
            <div>
              <span className="text-[#78756F]">Default embedding: </span>
              <span className="font-mono text-xs">{data.default_embedding}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

