import { useEffect, useMemo, useState } from 'react'
import Editor from '@monaco-editor/react'
import { CodeDiffView } from './CodeDiffView'

type Snapshot = { timestamp: number; code: string; elapsed_seconds: number }
type CheatEvent = { id: string; severity: 'low' | 'medium' | 'high'; event_type: string; occurred_at?: string; timestamp?: number }

type Props = {
  snapshots: Snapshot[]
  cheatEvents: CheatEvent[]
}

const formatMMSS = (seconds: number) => {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

export function ReplayTimeline({ snapshots, cheatEvents }: Props) {
  const [position, setPosition] = useState(0)
  const [playing, setPlaying] = useState(false)

  const duration = snapshots.length ? snapshots[snapshots.length - 1].elapsed_seconds : 0

  const currentIndex = useMemo(() => {
    if (!snapshots.length) return 0
    let best = 0
    let bestDist = Number.MAX_SAFE_INTEGER
    snapshots.forEach((s, idx) => {
      const d = Math.abs(s.elapsed_seconds - position)
      if (d < bestDist) {
        best = idx
        bestDist = d
      }
    })
    return best
  }, [position, snapshots])

  const current = snapshots[currentIndex] ?? { timestamp: 0, code: '', elapsed_seconds: 0 }
  const prev = snapshots[Math.max(0, currentIndex - 1)] ?? current

  useEffect(() => {
    if (!playing || duration <= 0) return
    const id = window.setInterval(() => {
      setPosition((p) => {
        if (p >= duration) {
          setPlaying(false)
          return duration
        }
        return Math.min(duration, p + 5) // 10x feel with 500ms tick.
      })
    }, 500)
    return () => window.clearInterval(id)
  }, [playing, duration])

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-100">Replay</h3>
        <span className="text-xs text-slate-400">
          {formatMMSS(position)} / {formatMMSS(duration)}
        </span>
      </div>

      <div className="relative">
        <input
          type="range"
          min={0}
          max={Math.max(duration, 1)}
          value={position}
          onChange={(e) => setPosition(Number(e.target.value))}
          className="w-full"
        />
        <div className="absolute inset-x-0 top-[-10px] h-8 pointer-events-none">
          {cheatEvents.map((e, idx) => {
            const ts = e.timestamp ?? (e.occurred_at ? Math.floor(new Date(e.occurred_at).getTime() / 1000) : 0)
            const rel = snapshots.length ? Math.max(0, ts - snapshots[0].timestamp) : 0
            const left = duration > 0 ? (rel / duration) * 100 : 0
            const color = e.severity === 'high' ? 'text-rose-400' : e.severity === 'medium' ? 'text-amber-300' : 'text-slate-400'
            return (
              <button
                key={`${e.id}-${idx}`}
                type="button"
                onClick={() => setPosition(Math.min(duration, rel))}
                className={`absolute top-0 -translate-x-1/2 text-[10px] ${color} pointer-events-auto`}
                style={{ left: `${left}%` }}
                title={`${e.event_type}`}
              >
                ▲
              </button>
            )
          })}
        </div>
      </div>

      <button
        onClick={() => setPlaying((v) => !v)}
        className="mt-2 rounded bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs text-slate-100"
      >
        {playing ? 'Pause' : 'Play 10x'}
      </button>

      <div className="mt-3">
        <Editor
          height="340px"
          defaultLanguage="python"
          value={current.code}
          theme="vs-dark"
          options={{ readOnly: true, minimap: { enabled: false }, automaticLayout: true }}
        />
      </div>

      <div className="mt-2 text-xs text-slate-500">Snapshot #{currentIndex + 1} at {formatMMSS(current.elapsed_seconds)}</div>
      <div className="mt-3">
        <CodeDiffView previousCode={prev.code} currentCode={current.code} />
      </div>
    </section>
  )
}

