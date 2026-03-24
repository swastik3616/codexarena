import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { InterviewQuestion } from '../../lib/candidateSession'

type Props = {
  question: InterviewQuestion | null
}

const difficultyClass: Record<string, string> = {
  easy: 'bg-emerald-600/20 text-emerald-300 border border-emerald-500/30',
  medium: 'bg-amber-600/20 text-amber-300 border border-amber-500/30',
  hard: 'bg-rose-600/20 text-rose-300 border border-rose-500/30',
}

const formatTime = (seconds: number) => {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

export const QuestionPanel = ({ question }: Props) => {
  const [elapsed, setElapsed] = useState(0)
  const [showExamples, setShowExamples] = useState(true)
  const [hintIdx, setHintIdx] = useState(0)
  const hints = question?.hints ?? []

  useEffect(() => {
    const id = window.setInterval(() => setElapsed((n) => n + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  const difficulty = (question?.difficulty ?? 'medium').toLowerCase()
  const diffCls = difficultyClass[difficulty] ?? difficultyClass.medium
  const examples = useMemo(() => question?.examples ?? [], [question])

  return (
    <section className="h-full bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-y-auto">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">{question?.title ?? 'Waiting for question...'}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`text-xs rounded px-2 py-0.5 ${diffCls}`}>{difficulty}</span>
            {(question?.topic_tags ?? []).map((tag) => (
              <span key={tag} className="text-xs rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-slate-400">Interview timer</p>
          <p className="font-mono text-sm text-slate-200">{formatTime(elapsed)}</p>
        </div>
      </div>

      <div className="prose prose-invert prose-sm max-w-none mt-4">
        <ReactMarkdown>{question?.description ?? 'Question will appear shortly after room activation.'}</ReactMarkdown>
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3">
        <button onClick={() => setShowExamples((v) => !v)} className="text-sm font-medium text-slate-200">
          {showExamples ? 'Hide examples' : 'Show examples'}
        </button>
        {showExamples && (
          <div className="mt-2 space-y-2">
            {!examples.length && <p className="text-xs text-slate-500">No examples provided.</p>}
            {examples.map((ex, idx) => (
              <div key={idx} className="rounded bg-slate-950 border border-slate-800 p-2 text-xs">
                <p className="text-slate-400">Input</p>
                <pre className="text-slate-200 whitespace-pre-wrap">{ex.input}</pre>
                <p className="text-slate-400 mt-2">Output</p>
                <pre className="text-slate-200 whitespace-pre-wrap">{ex.output}</pre>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3">
        <h3 className="text-sm font-medium text-slate-200">Hints</h3>
        {hints.length === 0 ? (
          <p className="text-xs text-slate-500 mt-2">No hints provided.</p>
        ) : (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-slate-300">{hints[hintIdx]}</p>
            <div className="flex items-center gap-2">
              <button
                disabled={hintIdx === 0}
                onClick={() => setHintIdx((n) => Math.max(0, n - 1))}
                className="rounded bg-slate-800 disabled:opacity-50 px-2 py-1 text-xs"
              >
                Prev
              </button>
              <button
                disabled={hintIdx >= hints.length - 1}
                onClick={() => setHintIdx((n) => Math.min(hints.length - 1, n + 1))}
                className="rounded bg-slate-800 disabled:opacity-50 px-2 py-1 text-xs"
              >
                Next
              </button>
              <span className="text-xs text-slate-500">
                {hintIdx + 1}/{hints.length}
              </span>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

