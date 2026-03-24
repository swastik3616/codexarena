type Props = {
  previousCode: string
  currentCode: string
}

export function CodeDiffView({ previousCode, currentCode }: Props) {
  const prev = previousCode.split('\n')
  const curr = currentCode.split('\n')
  const max = Math.max(prev.length, curr.length)
  const rows: Array<{ type: 'same' | 'add' | 'remove'; text: string }> = []

  for (let i = 0; i < max; i++) {
    const a = prev[i] ?? ''
    const b = curr[i] ?? ''
    if (a === b) rows.push({ type: 'same', text: `  ${b}` })
    else {
      if (a) rows.push({ type: 'remove', text: `- ${a}` })
      if (b) rows.push({ type: 'add', text: `+ ${b}` })
    }
  }

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <h4 className="text-sm font-semibold text-slate-200 mb-2">Snapshot Diff</h4>
      <pre className="text-xs max-h-56 overflow-auto rounded bg-slate-950 p-2">
        {rows.map((r, idx) => (
          <div
            key={idx}
            className={
              r.type === 'add'
                ? 'text-emerald-300 bg-emerald-900/10'
                : r.type === 'remove'
                  ? 'text-rose-300 bg-rose-900/10'
                  : 'text-slate-400'
            }
          >
            {r.text}
          </div>
        ))}
      </pre>
    </section>
  )
}

