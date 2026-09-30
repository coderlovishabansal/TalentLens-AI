import { useEffect, useState } from "react";
import { fetchJd, runRanking } from "./api";
import { CandidateCard } from "./components/CandidateCard";
import { ControlsPanel } from "./components/ControlsPanel";
import { JdPanel } from "./components/JdPanel";
import { ScoreChart } from "./components/ScoreChart";
import { StatsHeader } from "./components/StatsHeader";
import { buildSubmissionCsv, downloadCsv } from "./csv";
import type { JobDescription, RankRequest, RankResponse } from "./types";

const DEFAULT_FORM: RankRequest = {
  data_path: "sample_candidates.json",
  is_sample: true,
  top_n: 20,
  use_llm: false,
  llm_n: 30,
  coarse_n: 500,
};

export default function App() {
  const [form, setForm] = useState<RankRequest>(DEFAULT_FORM);
  const [jd, setJd] = useState<JobDescription | null>(null);
  const [result, setResult] = useState<RankResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJd()
      .then(setJd)
      .catch((e: Error) => setError(`Failed to load job description: ${e.message}`));
  }, []);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const data = await runRanking(form);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ranking failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <h1 className="text-2xl font-semibold text-slate-900">
            🎯 Redrob Intelligent Candidate Ranker
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            AI-powered candidate discovery &amp; ranking engine
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6 flex flex-col lg:flex-row gap-6">
        <ControlsPanel
          form={form}
          onChange={(patch) => setForm((f) => ({ ...f, ...patch }))}
          onRun={handleRun}
          loading={loading}
        />

        <div className="flex-1 min-w-0 flex flex-col gap-5">
          <JdPanel jd={jd} />

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
              {error}
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl px-4 py-8 text-center text-sm text-slate-500">
              Running ranking pipeline…
            </div>
          )}

          {!loading && !result && !error && (
            <div className="bg-white border border-dashed border-slate-300 rounded-xl px-4 py-12 text-center text-sm text-slate-400">
              Configure settings and click "Run Ranking" to get started.
            </div>
          )}

          {result && !loading && (
            <>
              <StatsHeader data={result} />
              <ScoreChart results={result.results} />

              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-900">
                  Top {result.top_n} Candidates
                </h2>
                <button
                  onClick={() =>
                    downloadCsv("submission.csv", buildSubmissionCsv(result.results))
                  }
                  className="text-sm font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 border border-violet-200 rounded-md px-3 py-1.5 transition-colors"
                >
                  ⬇️ Download submission.csv
                </button>
              </div>

              <div className="flex flex-col gap-3">
                {result.results.map((r) => (
                  <CandidateCard key={r.candidate_id} result={r} defaultOpen={r.rank <= 3} />
                ))}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
