type CheatEvent = {
  id: string
  severity: 'low' | 'medium' | 'high'
  event_type: string
  occurred_at?: string
  payload?: Record<string, unknown>
}

type Props = {
  events?: CheatEvent[]
}

const severityClass = {
  low: 'bg-slate-700 text-slate-200',
  medium: 'bg-amber-600/30 text-amber-300 border border-amber-500/30',
  high: 'bg-rose-600/30 text-rose-300 border border-rose-500/30',
}

export function CheatEventTimeline({ events = [] }: Props) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Cheat Event Timeline</h3>
      {events.length === 0 ? (
        <div className="rounded bg-emerald-900/20 border border-emerald-700/30 px-3 py-2 text-emerald-300 text-sm">
          ✓ No suspicious activity detected
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((e) => (
            <div key={e.id} className="relative pl-5">
              <span className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-slate-500" />
              <div className="rounded border border-slate-800 bg-slate-950 p-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className={`rounded px-2 py-0.5 ${severityClass[e.severity]}`}>{e.severity.toUpperCase()}</span>
                  <span className="text-slate-500">{e.occurred_at ? new Date(e.occurred_at).toLocaleString() : '-'}</span>
                </div>
                <p className="mt-1 text-slate-200">{e.event_type}</p>
                {e.payload && <pre className="mt-1 whitespace-pre-wrap text-slate-400">{JSON.stringify(e.payload)}</pre>}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

