import { useEffect } from 'react'
import axios from 'axios'
import { useNavigate, useParams } from 'react-router-dom'
import { getCandidateSession } from '../lib/candidateSession'

const API_BASE = 'http://127.0.0.1:8000'

export function WaitingRoom() {
  const { room_id } = useParams<{ room_id: string }>()
  const navigate = useNavigate()

  useEffect(() => {
    const session = getCandidateSession()
    if (!session || !room_id || session.roomId !== room_id) {
      navigate('/', { replace: true })
      return
    }

    const id = window.setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/rooms/${room_id}`, {
          headers: { Authorization: `Bearer ${session.candidateToken}` },
        })
        const status = String(res.data?.room?.status ?? '')
        if (status === 'active') {
          navigate(`/interview/${room_id}`)
        }
      } catch {
        // keep waiting
      }
    }, 3000)

    return () => window.clearInterval(id)
  }, [room_id, navigate])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Your interview is starting soon</h1>
        <div className="mt-5 inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse [animation-delay:150ms]" />
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}

