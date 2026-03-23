import type { ExecuteResult } from '../../hooks/useExecution'

type Props = {
  result: ExecuteResult | null
}

const statusLabel = (passed: boolean, timedOut: boolean) => {
  if (timedOut) return { text: 'TIMEOUT', cls: 'text-slate-400' }
  if (passed) return { text: 'PASS', cls: 'text-emerald-400' }
  return { text: 'FAIL', cls: 'text-rose-400' }
}

export const TestResults = ({ result }: Props) => {
  if (!result) return null

  const pct = result.total > 0 ? Math.round((result.pass_count / result.total) * 100) : 0

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-slate-100 font-semibold">Test Results</h3>
        <span className="text-sm text-slate-300">
          {result.pass_count} / {result.total} tests passed
        </span>
      </div>

      <div className="w-full h-2 bg-slate-800 rounded">
        <div className="h-2 bg-emerald-500 rounded" style={{ width: `${pct}%` }} />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800">
              <th className="text-left py-2">Test #</th>
              <th className="text-left py-2">Status</th>
              <th className="text-left py-2">Time (ms)</th>
            </tr>
          </thead>
          <tbody>
            {result.results.map((r) => {
              const status = statusLabel(r.passed, result.timed_out)
              return (
                <tr key={String(r.test_id)} className="border-b border-slate-900 text-slate-200">
                  <td className="py-2">{String(r.test_id)}</td>
                  <td className={`py-2 font-medium ${status.cls}`}>{status.text}</td>
                  <td className="py-2">{r.time_ms}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <details className="bg-slate-950 rounded border border-slate-800">
        <summary className="cursor-pointer px-3 py-2 text-slate-300">stdout</summary>
        <pre className="px-3 pb-3 text-xs text-slate-200 whitespace-pre-wrap">{result.stdout || '(empty)'}</pre>
      </details>

      <details className="bg-slate-950 rounded border border-slate-800">
        <summary className="cursor-pointer px-3 py-2 text-slate-300">stderr</summary>
        <pre className="px-3 pb-3 text-xs text-slate-200 whitespace-pre-wrap">{result.stderr || '(empty)'}</pre>
      </details>
    </section>
  )
}

