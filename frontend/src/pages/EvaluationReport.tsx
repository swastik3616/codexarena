import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Navigate, useParams } from 'react-router-dom'
import { AIFeedback } from '../components/dashboard/AIFeedback'
import { BigODisplay } from '../components/dashboard/BigODisplay'
import { CheatEventTimeline } from '../components/dashboard/CheatEventTimeline'
import { ScoreBreakdown } from '../components/dashboard/ScoreBreakdown'
import { TestResultsSummary } from '../components/dashboard/TestResultsSummary'

const API_BASE = 'http://127.0.0.1:8000'

type ReportData = {
  attempt: { id: string; language?: string; submitted_at?: string }
  evaluation: {
    correctness_score: number
    efficiency_score: number
    readability_score: number
    edge_case_score: number
    total_score: number
    big_o_time?: string
    big_o_space?: string
    feedback?: string
    suggestions?: string[]
    evaluated_at?: string
    prompt_version?: string
  }
  execution: {
    test_pass_count: number
    test_total: number
    wall_time_ms?: number
    memory_kb?: number
    rows?: Array<{ id: string | number; status: 'pass' | 'fail' | 'timeout'; expected?: string; actual?: string; time_ms?: number }>
  }
  cheat_events: Array<{ id: string; severity: 'low' | 'medium' | 'high'; event_type: string; occurred_at?: string; payload?: Record<string, unknown> }>
}

const fallbackData: ReportData = {
  attempt: { id: 'demo-attempt', language: 'python' },
  evaluation: {
    correctness_score: 32,
    efficiency_score: 21,
    readability_score: 15,
    edge_case_score: 8,
    total_score: 76,
    big_o_time: 'O(n)',
    big_o_space: 'O(n)',
    feedback: 'The solution is correct and efficient for common scenarios. Edge-case handling is mostly sound with room for clearer assumptions.',
    suggestions: ['Add guard clauses for empty input.', 'Improve naming for intermediate variables.', 'Document edge-case behavior explicitly.'],
    prompt_version: 'v1',
  },
  execution: { test_pass_count: 6, test_total: 8, wall_time_ms: 142, memory_kb: 14, rows: [] },
  cheat_events: [],
}

export function EvaluationReport() {
  const { attempt_id } = useParams<{ attempt_id: string }>()
  const recruiterToken = localStorage.getItem('recruiterToken')
  const [data, setData] = useState<ReportData>(fallbackData)

  useEffect(() => {
    const load = async () => {
      if (!attempt_id || !recruiterToken) return
      try {
        // Preferred API if implemented server-side.
        const res = await axios.get(`${API_BASE}/api/attempts/${attempt_id}/report`, {
          headers: { Authorization: `Bearer ${recruiterToken}` },
        })
        setData(res.data as ReportData)
      } catch {
        // Keep fallback render for now.
      }
    }
    void load()
  }, [attempt_id, recruiterToken])

  const total = useMemo(
    () =>
      data.evaluation.correctness_score +
      data.evaluation.efficiency_score +
      data.evaluation.readability_score +
      data.evaluation.edge_case_score,
    [data],
  )

  if (!recruiterToken) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs text-slate-400">Attempt</p>
          <p className="text-sm font-medium">{attempt_id}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Language</p>
          <p className="text-sm">{data.attempt.language ?? 'python'}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Overall Score</p>
          <p className="text-2xl font-bold text-blue-300">{total}/100</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="space-y-4">
          <ScoreBreakdown
            correctness={data.evaluation.correctness_score}
            efficiency={data.evaluation.efficiency_score}
            readability={data.evaluation.readability_score}
            edgeCases={data.evaluation.edge_case_score}
          />
          <BigODisplay timeComplexity={data.evaluation.big_o_time} spaceComplexity={data.evaluation.big_o_space} />
        </div>

        <div className="space-y-4">
          <AIFeedback
            feedback={data.evaluation.feedback}
            suggestions={data.evaluation.suggestions}
            evaluatedAt={data.evaluation.evaluated_at}
            promptVersion={data.evaluation.prompt_version}
          />
          <TestResultsSummary
            passCount={data.execution.test_pass_count}
            total={data.execution.test_total}
            executionMs={data.execution.wall_time_ms}
            memoryKb={data.execution.memory_kb}
            rows={data.execution.rows}
          />
        </div>

        <div className="space-y-4">
          <CheatEventTimeline events={data.cheat_events} />
        </div>
      </div>
    </div>
  )
}

