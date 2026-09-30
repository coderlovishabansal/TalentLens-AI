import type { CandidateResult } from "./types";

export function buildSubmissionCsv(results: CandidateResult[]): string {
  const lines = ["candidate_id,rank,score,reasoning"];
  let prevScore: number | null = null;

  for (const r of results) {
    let score = r.display_score;
    if (prevScore !== null && score > prevScore) score = prevScore;
    prevScore = score;
    const reasoning = r.reasoning.replace(/,/g, ";").replace(/"/g, "'");
    lines.push(`${r.candidate_id},${r.rank},${score},"${reasoning}"`);
  }

  return lines.join("\n");
}

export function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
