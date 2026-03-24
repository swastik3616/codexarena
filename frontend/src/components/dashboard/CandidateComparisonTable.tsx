import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export type AnalyticsCandidate = {
  id: string
  attempt_id?: string | null
  name: string
  status: string
  scores: { correctness: number; efficiency: number; readability: number; edge_cases: number; total: number }
  execution: { pass_count: number; total: number; wall_time_ms: number }
  cheat_event_count: number
  time_to_first_submit_seconds?: number | null
}

type Props = {
  candidates: AnalyticsCandidate[]
}

type SortKey = 'name' | 'total' | 'correctness' | 'efficiency' | 'readability' | 'edge_cases' | 'tests' | 'cheats' | 'submit_time'

export function CandidateComparisonTable({ candidates }: Props) {
  const navigate = useNavigate()
  const [sortKey, setSortKey] = useState<SortKey>('total')
  const [asc, setAsc] = useState(false)

  const max = useMemo(() => {
    const pick = (fn: (c: AnalyticsCandidate) => number) => Math.max(0, ...candidates.map(fn))
    return {
      total: pick((c) => c.scores.total),
      correctness: pick((c) => c.scores.correctness),
      efficiency: pick((c) => c.scores.efficiency),
      readability: pick((c) => c.scores.readability),
      edge_cases: pick((c) => c.scores.edge_cases),
    }
  }, [candidates])

  const sorted = useMemo(() => {
    const arr = [...candidates]
    const value = (c: AnalyticsCandidate): string | number => {
      if (sortKey === 'name') return c.name.toLowerCase()
      if (sortKey === 'total') return c.scores.total
      if (sortKey === 'correctness') return c.scores.correctness
      if (sortKey === 'efficiency') return c.scores.efficiency
      if (sortKey === 'readability') return c.scores.readability
      if (sortKey === 'edge_cases') return c.scores.edge_cases
      if (sortKey === 'tests') return c.execution.pass_count
      if (sortKey === 'cheats') return c.cheat_event_count
      return c.time_to_first_submit_seconds ?? Number.MAX_SAFE_INTEGER
    }
    arr.sort((a, b) => {
      const va = value(a)
      const vb = value(b)
      if (typeof va === 'string' && typeof vb === 'string') return asc ? va.localeCompare(vb) : vb.localeCompare(va)
      return asc ? Number(va) - Number(vb) : Number(vb) - Number(va)
    })
    return arr
  }, [candidates, sortKey, asc])

  const sortBy = (key: SortKey) => {
    if (sortKey === key) setAsc((v) => !v)
    else {
      setSortKey(key)
      setAsc(false)
    }
  }

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-3 overflow-auto">
      <h3 className="text-sm font-semibold text-slate-100 mb-2">Candidate Comparison</h3>
      <table className="w-full text-xs min-w-[980px]">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2 cursor-pointer" onClick={() => sortBy('name')}>Name</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('total')}>Total</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('correctness')}>Correctness</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('efficiency')}>Efficiency</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('readability')}>Readability</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('edge_cases')}>Edge Cases</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('tests')}>Tests Passed</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('cheats')}>Cheat Events</th>
            <th className="py-2 cursor-pointer" onClick={() => sortBy('submit_time')}>Time to Submit</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr
              key={c.id}
              className="border-b border-slate-800/60 text-slate-200 hover:bg-slate-800/40 cursor-pointer"
              onClick={() => c.attempt_id && navigate(`/report/${c.attempt_id}`)}
            >
              <td className="py-2">{c.name}</td>
              <td className={`py-2 ${c.scores.total === max.total ? 'bg-emerald-900/30' : ''}`}>{c.scores.total}</td>
              <td className={`py-2 ${c.scores.correctness === max.correctness ? 'bg-blue-900/30' : ''}`}>{c.scores.correctness}</td>
              <td className={`py-2 ${c.scores.efficiency === max.efficiency ? 'bg-green-900/30' : ''}`}>{c.scores.efficiency}</td>
              <td className={`py-2 ${c.scores.readability === max.readability ? 'bg-purple-900/30' : ''}`}>{c.scores.readability}</td>
              <td className={`py-2 ${c.scores.edge_cases === max.edge_cases ? 'bg-amber-900/30' : ''}`}>{c.scores.edge_cases}</td>
              <td className="py-2">
                {c.execution.pass_count}/{c.execution.total}
              </td>
              <td className="py-2">{c.cheat_event_count}</td>
              <td className="py-2">{c.time_to_first_submit_seconds ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

