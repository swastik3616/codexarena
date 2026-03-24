import { useEffect, useState } from 'react'
import axios from 'axios'
import { Navigate, useParams } from 'react-router-dom'
import { CandidateComparisonTable, type AnalyticsCandidate } from '../components/dashboard/CandidateComparisonTable'
import { ScoreDistributionChart } from '../components/dashboard/ScoreDistributionChart'
import { CheatSummaryCard } from '../components/dashboard/CheatSummaryCard'

const API_BASE = 'http://127.0.0.1:8000'

type AnalyticsResponse = {
  room: { id: string; title: string; created_at?: string; candidate_count: number }
  candidates: AnalyticsCandidate[]
  question?: { title?: string; difficulty?: string; topic_tags?: string[] }
}

export function RoomAnalytics() {
  const { room_id } = useParams<{ room_id: string }>()
  const recruiterToken = localStorage.getItem('recruiterToken')
  const [data, setData] = useState<AnalyticsResponse | null>(null)

  useEffect(() => {
    const load = async () => {
      if (!room_id || !recruiterToken) return
      const res = await axios.get(`${API_BASE}/rooms/${room_id}/analytics`, {
        headers: { Authorization: `Bearer ${recruiterToken}` },
      })
      setData(res.data as AnalyticsResponse)
    }
    void load()
  }, [room_id, recruiterToken])

  if (!recruiterToken) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 space-y-4">
      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h1 className="text-lg font-semibold">{data?.room.title ?? 'Room Analytics'}</h1>
        <p className="text-xs text-slate-400 mt-1">Candidates: {data?.room.candidate_count ?? 0}</p>
        <p className="text-xs text-slate-500 mt-1">
          Question: {data?.question?.title ?? '-'} {data?.question?.difficulty ? `(${data.question.difficulty})` : ''}
        </p>
      </section>

      <CandidateComparisonTable candidates={data?.candidates ?? []} />
      <ScoreDistributionChart candidates={data?.candidates ?? []} />
      <CheatSummaryCard candidates={data?.candidates ?? []} />
    </div>
  )
}

