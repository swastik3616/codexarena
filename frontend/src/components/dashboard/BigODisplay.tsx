type Props = {
  timeComplexity?: string
  spaceComplexity?: string
}

const scoreClass = (value: string) => {
  const v = value.toLowerCase().replace(/\s/g, '')
  if (v.includes('o(1)') || v.includes('o(logn)') || v === 'o(n)') return 'text-emerald-300'
  if (v.includes('o(nlogn)')) return 'text-amber-300'
  return 'text-rose-300'
}

export function BigODisplay({ timeComplexity = 'N/A', spaceComplexity = 'N/A' }: Props) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Complexity Analysis</h3>
      <div className="space-y-3">
        <div className="rounded bg-slate-950 p-3">
          <p className="text-xs text-slate-400">Time complexity</p>
          <p className={`text-lg font-semibold ${scoreClass(timeComplexity)}`}>{timeComplexity}</p>
          <span className="inline-block mt-1 rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
            Derived from algorithm path and loop nesting
          </span>
        </div>
        <div className="rounded bg-slate-950 p-3">
          <p className="text-xs text-slate-400">Space complexity</p>
          <p className={`text-lg font-semibold ${scoreClass(spaceComplexity)}`}>{spaceComplexity}</p>
        </div>
      </div>
    </section>
  )
}

