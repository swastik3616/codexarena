type Props = {
  feedback?: string
  suggestions?: string[]
  evaluatedAt?: string
  promptVersion?: string
}

export function AIFeedback({ feedback, suggestions = [], evaluatedAt, promptVersion }: Props) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">AI Feedback</h3>
      <blockquote className="rounded border-l-4 border-blue-500 bg-slate-950 px-3 py-3 text-sm text-slate-200">
        {feedback ?? 'No feedback generated yet.'}
      </blockquote>
      <ol className="mt-3 list-decimal pl-5 space-y-1 text-sm text-slate-300">
        {suggestions.length === 0 && <li>No specific suggestions available.</li>}
        {suggestions.map((s, idx) => (
          <li key={idx}>{s}</li>
        ))}
      </ol>
      <div className="mt-3 text-xs text-slate-500 flex items-center justify-between">
        <span>Evaluated: {evaluatedAt ? new Date(evaluatedAt).toLocaleString() : 'N/A'}</span>
        <span>Prompt: {promptVersion ?? 'v1'}</span>
      </div>
    </section>
  )
}

