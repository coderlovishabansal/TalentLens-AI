import type { RankRequest } from "../types";

interface ControlsPanelProps {
  form: RankRequest;
  onChange: (patch: Partial<RankRequest>) => void;
  onRun: () => void;
  loading: boolean;
}

export function ControlsPanel({ form, onChange, onRun, loading }: ControlsPanelProps) {
  return (
    <aside className="w-full lg:w-72 shrink-0 bg-white border border-slate-200 rounded-xl p-5 h-fit lg:sticky lg:top-6">
      <h2 className="text-sm font-semibold text-slate-900 mb-4 uppercase tracking-wide">
        Settings
      </h2>

      <label className="block text-xs font-medium text-slate-600 mb-1">
        Candidates file path
      </label>
      <input
        type="text"
        value={form.data_path}
        onChange={(e) => onChange({ data_path: e.target.value })}
        className="w-full mb-3 rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
      />

      <label className="flex items-center gap-2 mb-4 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={form.is_sample}
          onChange={(e) => onChange({ is_sample: e.target.checked })}
          className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-400"
        />
        Sample JSON file (not .jsonl.gz)
      </label>

      <label className="block text-xs font-medium text-slate-600 mb-1">
        Top N candidates:{" "}
        <span className="font-mono text-slate-900">{form.top_n}</span>
      </label>
      <input
        type="range"
        min={10}
        max={100}
        step={5}
        value={form.top_n}
        onChange={(e) => onChange({ top_n: Number(e.target.value) })}
        className="w-full mb-4 accent-violet-600"
      />

      <label className="flex items-center gap-2 mb-3 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={form.use_llm}
          onChange={(e) => onChange({ use_llm: e.target.checked })}
          className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-400"
        />
        Enable Claude LLM re-ranking
      </label>
      <p className="text-[11px] text-slate-400 mb-3 -mt-2">
        Requires ANTHROPIC_API_KEY on the server
      </p>

      <label className="block text-xs font-medium text-slate-600 mb-1">
        LLM re-ranking pool size:{" "}
        <span className="font-mono text-slate-900">{form.llm_n}</span>
      </label>
      <input
        type="range"
        min={10}
        max={100}
        step={5}
        value={form.llm_n}
        disabled={!form.use_llm}
        onChange={(e) => onChange({ llm_n: Number(e.target.value) })}
        className="w-full mb-5 accent-violet-600 disabled:opacity-40"
      />

      <button
        onClick={onRun}
        disabled={loading}
        className="w-full rounded-md bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white text-sm font-semibold py-2.5 transition-colors"
      >
        {loading ? "Ranking…" : "🚀 Run Ranking"}
      </button>
    </aside>
  );
}
