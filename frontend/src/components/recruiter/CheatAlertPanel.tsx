import { useEffect, useRef } from 'react'
import type { CheatEvent } from '../../store/roomStore'

type Props = {
  events: CheatEvent[]
}

const badgeClass: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: 'bg-slate-700 text-slate-200',
  MEDIUM: 'bg-amber-600/30 text-amber-300 border border-amber-500/30',
  HIGH: 'bg-rose-600/30 text-rose-300 border border-rose-500/30',
}

export const CheatAlertPanel = ({ events }: Props) => {
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <section className="bg-slate-950 border border-slate-800 rounded-lg p-3">
      <h4 className="text-sm font-semibold text-slate-200 mb-3">Cheat Alerts</h4>
      <div className="max-h-44 overflow-y-auto space-y-2 pr-1">
        {events.length === 0 && <p className="text-xs text-slate-500">No cheat events yet.</p>}
        {events.map((e) => (
          <div key={e.id} className="rounded border border-slate-800 bg-slate-900 px-2 py-2 text-xs">
            <div className="flex items-center justify-between">
              <span className={`rounded px-2 py-0.5 font-medium ${badgeClass[e.severity]}`}>{e.severity}</span>
              <span className="text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="mt-1 text-slate-300">{e.eventType}</p>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </section>
  )
}

