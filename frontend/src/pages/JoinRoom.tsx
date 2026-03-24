import { useState } from 'react'
import axios from 'axios'
import { useNavigate, useParams } from 'react-router-dom'
import { setCandidateSession } from '../lib/candidateSession'

const API_BASE = 'http://127.0.0.1:8000'

export function JoinRoom() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const join = async () => {
    if (!token || !name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const resolved = await axios.get(`${API_BASE}/rooms/resolve/${token}`)
      const roomId = resolved.data.room_id as string

      const res = await axios.post(`${API_BASE}/rooms/${roomId}/join`, {
        name: name.trim(),
        join_token: token,
      })

      setCandidateSession({
        roomId,
        candidateId: res.data.candidate_id,
        candidateToken: res.data.candidate_token,
        attemptId: res.data.attempt_id,
        question: res.data.question ?? undefined,
      })

      navigate(`/waiting/${roomId}`)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Unable to join interview')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-lg p-5">
        <h1 className="text-xl font-semibold">Join Interview</h1>
        <p className="text-sm text-slate-400 mt-1">Enter your name to begin.</p>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          className="mt-4 w-full rounded bg-slate-950 border border-slate-800 px-3 py-2 text-sm"
        />
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        <button
          onClick={join}
          disabled={loading || !name.trim()}
          className="mt-4 w-full rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-2 text-sm font-medium"
        >
          {loading ? 'Joining...' : 'Join Interview'}
        </button>
      </div>
    </div>
  )
}

