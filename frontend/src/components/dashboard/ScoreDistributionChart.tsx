import type { AnalyticsCandidate } from './CandidateComparisonTable'

type Props = {
  candidates: AnalyticsCandidate[]
}

const barClass = (score: number) => (score > 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-rose-500')

export function ScoreDistributionChart({ candidates }: Props) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Score Distribution</h3>
      <div className="space-y-2">
        {candidates.map((c) => (
          <div key={c.id} className="grid grid-cols-[140px_1fr_40px] items-center gap-2">
            <span className="text-xs text-slate-300 truncate">{c.name}</span>
            <div className="h-3 rounded bg-slate-800 overflow-hidden">
              <div className={`h-full ${barClass(c.scores.total)}`} style={{ width: `${Math.max(0, Math.min(100, c.scores.total))}%` }} />
            </div>
            <span className="text-xs text-slate-300 text-right">{c.scores.total}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 text-[11px] text-slate-500">X axis: score (0-100), Y axis: candidate names</div>
    </section>
  )
}

