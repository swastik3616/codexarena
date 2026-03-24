import { useState } from 'react'

type TestRow = {
  id: string | number
  status: 'pass' | 'fail' | 'timeout'
  expected?: string
  actual?: string
  time_ms?: number
}

type Props = {
  passCount: number
  total: number
  executionMs?: number
  memoryKb?: number
  rows?: TestRow[]
}

export function TestResultsSummary({ passCount, total, executionMs, memoryKb, rows = [] }: Props) {
  const [expanded, setExpanded] = useState(false)
  const pct = total > 0 ? Math.round((passCount / total) * 100) : 0

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Execution Summary</h3>
      <p className="text-sm text-slate-200 mb-2">
        {passCount}/{total} tests passed
      </p>
      <div className="h-2 w-full rounded bg-slate-800 overflow-hidden">
        <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded bg-slate-950 px-2 py-1">Execution time: {executionMs ?? 0}ms</div>
        <div className="rounded bg-slate-950 px-2 py-1">Memory: {memoryKb ?? 0}KB</div>
      </div>
      <button onClick={() => setExpanded((v) => !v)} className="mt-3 text-xs text-blue-300">
        {expanded ? 'Hide test case details' : 'Show test case details'}
      </button>
      {expanded && (
        <div className="mt-2 overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-800">
                <th className="py-1">Case</th>
                <th className="py-1">Status</th>
                <th className="py-1">Expected</th>
                <th className="py-1">Actual</th>
                <th className="py-1">Time</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={String(r.id)} className="border-b border-slate-800/60 text-slate-300">
                  <td className="py-1">{r.id}</td>
                  <td className="py-1">{r.status}</td>
                  <td className="py-1">{r.expected ?? '-'}</td>
                  <td className="py-1">{r.actual ?? '-'}</td>
                  <td className="py-1">{r.time_ms ?? 0}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

