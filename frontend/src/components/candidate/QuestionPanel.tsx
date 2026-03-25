import { useEffect, useState } from 'react'
import type { InterviewQuestion } from '../../lib/candidateSession'

type Props = {
  question: InterviewQuestion | null
}

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: 'text-emerald-400 bg-emerald-400/10 border border-emerald-500/20',
  medium: 'text-amber-400 bg-amber-400/10 border border-amber-500/20',
  hard: 'text-rose-400 bg-rose-400/10 border border-rose-500/20',
}

const formatTime = (s: number) =>
  `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

/** Converts backtick-wrapped words to inline <code> spans */
function InlineText({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g)
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith('`') && part.endsWith('`') ? (
          <code
            key={i}
            className="px-1 py-0.5 rounded bg-slate-700 text-slate-200 font-mono text-[0.82em]"
          >
            {part.slice(1, -1)}
          </code>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

export const QuestionPanel = ({ question }: Props) => {
  const [elapsed, setElapsed] = useState(0)
  const [showHint, setShowHint] = useState(false)
  const [hintIdx, setHintIdx] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => setElapsed((n) => n + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  const difficulty = (question?.difficulty ?? 'medium').toLowerCase()
  const diffStyle = DIFFICULTY_STYLE[difficulty] ?? DIFFICULTY_STYLE.medium
  const hints = question?.hints ?? []
  const examples = question?.examples ?? []
  const constraints = question?.constraints ?? []
  const tags = question?.topic_tags ?? []

  const descLines = (question?.description ?? '').split('\n').filter(Boolean)

  return (
    <section className="h-full flex flex-col bg-[#1a1a2e] border border-slate-800/60 rounded-xl overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/60 bg-slate-900/50">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-300">Interview</span>
        </div>
        <div className="font-mono text-sm text-slate-300 tabular-nums">
          ⏱ {formatTime(elapsed)}
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {!question ? (
          <div className="flex items-center justify-center h-32">
            <p className="text-slate-500 text-sm animate-pulse">Waiting for question…</p>
          </div>
        ) : (
          <>
            {/* Title + difficulty */}
            <div>
              <h2 className="text-xl font-bold text-white leading-snug">
                {question.title}
              </h2>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize ${diffStyle}`}>
                  {difficulty}
                </span>
                {tags.map((tag) => (
                  <button
                    key={tag}
                    className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                  >
                    {tag}
                  </button>
                ))}
                {hints.length > 0 && (
                  <button
                    onClick={() => setShowHint((v) => !v)}
                    className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-amber-400 hover:bg-slate-700 transition flex items-center gap-1"
                  >
                    <span>💡</span> Hint
                  </button>
                )}
              </div>

              {/* Inline hint reveal */}
              {showHint && hints.length > 0 && (
                <div className="mt-3 rounded-lg bg-amber-500/10 border border-amber-500/20 px-4 py-3 text-sm text-amber-300">
                  <p>{hints[hintIdx]}</p>
                  {hints.length > 1 && (
                    <div className="mt-2 flex items-center gap-2 text-xs">
                      <button
                        disabled={hintIdx === 0}
                        onClick={() => setHintIdx((n) => Math.max(0, n - 1))}
                        className="disabled:opacity-40 hover:text-amber-200"
                      >
                        ← Prev
                      </button>
                      <span className="text-amber-500">{hintIdx + 1}/{hints.length}</span>
                      <button
                        disabled={hintIdx >= hints.length - 1}
                        onClick={() => setHintIdx((n) => Math.min(hints.length - 1, n + 1))}
                        className="disabled:opacity-40 hover:text-amber-200"
                      >
                        Next →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Description */}
            <div className="text-sm text-slate-300 leading-relaxed space-y-2">
              {descLines.map((line, i) => (
                <p key={i}>
                  <InlineText text={line} />
                </p>
              ))}
            </div>

            {/* Examples */}
            {examples.length > 0 && (
              <div className="space-y-4">
                {examples.map((ex, idx) => (
                  <div key={idx}>
                    <p className="text-sm font-semibold text-slate-200 mb-2">
                      Example {idx + 1}:
                    </p>
                    <div className="rounded-lg bg-slate-800/60 border border-slate-700/50 px-4 py-3 font-mono text-sm space-y-1">
                      <div>
                        <span className="font-bold text-slate-200">Input:</span>{' '}
                        <span className="text-slate-300">{ex.input}</span>
                      </div>
                      <div>
                        <span className="font-bold text-slate-200">Output:</span>{' '}
                        <span className="text-slate-300">{ex.output}</span>
                      </div>
                      {ex.explanation && (
                        <div>
                          <span className="font-bold text-slate-200">Explanation:</span>{' '}
                          <span className="text-slate-400">{ex.explanation}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Constraints */}
            {constraints.length > 0 && (
              <div>
                <p className="text-sm font-bold text-slate-200 mb-3">Constraints:</p>
                <ul className="space-y-1.5">
                  {constraints.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-slate-500 shrink-0" />
                      <code className="font-mono text-xs bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                        {c}
                      </code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
