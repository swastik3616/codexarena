import type { AnalyticsCandidate } from './CandidateComparisonTable'

type Props = {
  candidates: AnalyticsCandidate[]
}

export function CheatSummaryCard({ candidates }: Props) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Cheat Summary</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
        {candidates.map((c) => {
          const hasHigh = c.cheat_event_count > 0
          return (
            <div key={c.id} className="rounded border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-200">{c.name}</p>
                <span className={`h-2.5 w-2.5 rounded-full ${hasHigh ? 'bg-rose-500' : 'bg-emerald-500'}`} />
              </div>
              <p className="mt-1 text-xs text-slate-400">{hasHigh ? `${c.cheat_event_count} events` : 'Clean session'}</p>
              {c.attempt_id ? (
                <a className="mt-2 inline-block text-xs text-blue-300 hover:underline" href={`/report/${c.attempt_id}`}>
                  View Details
                </a>
              ) : (
                <span className="mt-2 inline-block text-xs text-slate-500">View Details</span>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

