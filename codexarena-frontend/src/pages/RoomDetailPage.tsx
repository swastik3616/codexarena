import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Users, Activity, ChevronLeft, Maximize2, Terminal } from 'lucide-react'

// Mock types for candidate state
type CandidateState = {
  id: string
  name: string
  code: string
  lastActive: string
  status: 'online' | 'offline'
}

export const RoomDetailPage = () => {
  const { roomId } = useParams()
  const [candidates, setCandidates] = useState<Record<string, CandidateState>>({})
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Connect as a "recruiter/monitor" to receive all broadcasts for this room
    // In a real app, you'd have a separate secure endpoint or role-based auth for this.
    const ws = new WebSocket(`ws://localhost:8000/ws/room/${roomId}?candidate_name=Recruiter`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'candidate_joined') {
        setCandidates(prev => ({
          ...prev,
          [data.candidate_id]: {
            id: data.candidate_id,
            name: data.candidate_name,
            code: '',
            lastActive: new Date().toLocaleTimeString(),
            status: 'online'
          }
        }))
      } else if (data.type === 'candidate_left') {
        setCandidates(prev => ({
          ...prev,
          [data.candidate_id]: { ...prev[data.candidate_id], status: 'offline' }
        }))
      } else if (data.type === 'code_update' && data.candidate_id) {
        setCandidates(prev => {
          // If we receive an update from a candidate we haven't seen yet
          const existing = prev[data.candidate_id] || { 
            id: data.candidate_id, 
            name: 'Unknown Candidate',
            status: 'online' 
          }
          
          return {
            ...prev,
            [data.candidate_id]: {
              ...existing,
              code: data.payload.code,
              lastActive: new Date().toLocaleTimeString(),
              status: 'online'
            }
          }
        })
      }
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [roomId])

  const candidateList = Object.values(candidates)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-2">
        <Link to="/rooms" className="p-2 hover:bg-slate-200 rounded-lg text-slate-500 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Room: {roomId}</h2>
          <div className="flex items-center gap-4 mt-1 text-sm text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Live Monitoring
            </span>
            <span className="flex items-center gap-1.5">
              <Users className="w-4 h-4" /> {candidateList.length} Active Candidates
            </span>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 mb-6">
        <p className="text-slate-600">
          <strong>Share this link to invite candidates:</strong><br />
          <code className="bg-slate-100 px-3 py-1.5 rounded-lg text-blue-600 mt-2 inline-block font-mono text-sm border border-slate-200">
            http://localhost:5174/join/{roomId}
          </code>
        </p>
      </div>

      {candidateList.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-100 p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
          <Activity className="w-12 h-12 text-slate-300 mb-4 animate-pulse" />
          <h3 className="text-lg font-semibold text-slate-800 mb-1">Waiting for candidates...</h3>
          <p className="text-slate-500">When candidates join using the link above, their live code output will appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {candidateList.map(candidate => (
            <div key={candidate.id} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[400px]">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm">
                    {candidate.name.substring(0,2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800 text-sm leading-tight">{candidate.name}</h3>
                    <p className="text-xs text-slate-500">Last active: {candidate.lastActive}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${candidate.status === 'online' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
                    {candidate.status}
                  </span>
                  <button className="text-slate-400 hover:text-slate-700 transition-colors">
                    <Maximize2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="flex-1 bg-[#1e1e1e] p-4 overflow-auto font-mono text-sm text-slate-300 relative">
                <div className="absolute top-2 right-2 text-xs text-[#5c5c5c] flex items-center gap-1">
                  <Terminal className="w-3 h-3" /> Live
                </div>
                <pre><code>{candidate.code || '# Candidate has not typed anything yet...'}</code></pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
