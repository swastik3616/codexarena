import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { CandidateCard } from '../components/recruiter/CandidateCard'
import { CandidateLiveView } from '../components/recruiter/CandidateLiveView'
import { RoomControls } from '../components/recruiter/RoomControls'
import { useRoomWebSocket } from '../hooks/useRoomWebSocket'
import { useRoomStore } from '../store/roomStore'

const API_BASE = 'http://127.0.0.1:8000'

export function RecruiterDashboard() {
  const [params] = useSearchParams()
  const recruiterToken = params.get('token') ?? localStorage.getItem('recruiterToken') ?? undefined
  if (recruiterToken) localStorage.setItem('recruiterToken', recruiterToken)

  const rooms = useRoomStore((s) => s.rooms)
  const setRooms = useRoomStore((s) => s.setRooms)
  const selectedRoomId = useRoomStore((s) => s.selectedRoomId)
  const selectRoom = useRoomStore((s) => s.selectRoom)
  const selectedCandidateId = useRoomStore((s) => s.selectedCandidateId)
  const selectCandidate = useRoomStore((s) => s.selectCandidate)
  const markCandidateCheatRead = useRoomStore((s) => s.markCandidateCheatRead)
  const upsertCandidate = useRoomStore((s) => s.upsertCandidate)
  const candidatesByRoom = useRoomStore((s) => s.candidatesByRoom)
  const cheatEventsByRoom = useRoomStore((s) => s.cheatEventsByRoom)

  const selectedRoom = rooms.find((r) => r.id === selectedRoomId) ?? null
  const candidates = selectedRoomId ? candidatesByRoom[selectedRoomId] ?? [] : []
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId) ?? null
  const candidateEvents = useMemo(
    () =>
      (selectedRoomId ? cheatEventsByRoom[selectedRoomId] ?? [] : []).filter(
        (e) => e.candidateId === selectedCandidateId,
      ),
    [selectedRoomId, selectedCandidateId, cheatEventsByRoom],
  )

  useRoomWebSocket({ roomId: selectedRoomId, recruiterToken, wsBase: 'ws://127.0.0.1:8000/ws' })

  useEffect(() => {
    const loadRooms = async () => {
      if (!recruiterToken) return
      const res = await axios.get(`${API_BASE}/rooms`, {
        headers: { Authorization: `Bearer ${recruiterToken}` },
      })
      const loaded = (res.data.items ?? []).map((r: any) => ({
        id: String(r.room_id),
        title: String(r.title),
        difficulty: r.difficulty,
        status: String(r.status),
        joinLink: r.join_link,
      }))
      setRooms(loaded)
      if (!selectedRoomId && loaded.length) selectRoom(loaded[0].id)
    }
    void loadRooms()
  }, [recruiterToken, setRooms, selectRoom, selectedRoomId])

  useEffect(() => {
    const loadCandidates = async () => {
      if (!selectedRoomId || !recruiterToken) return
      const res = await axios.get(`${API_BASE}/rooms/${selectedRoomId}`, {
        headers: { Authorization: `Bearer ${recruiterToken}` },
      })
      ;(res.data.candidates ?? []).forEach((c: any) => {
        upsertCandidate(selectedRoomId, {
          id: String(c.candidate_id),
          name: String(c.name ?? 'Candidate'),
          status: (c.status ?? 'waiting') as 'waiting' | 'coding' | 'submitted' | 'evaluated',
        })
      })
    }
    void loadCandidates()
  }, [selectedRoomId, recruiterToken, upsertCandidate])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 p-4">
        <aside className="space-y-3">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
            <h2 className="text-sm font-semibold mb-2">Rooms</h2>
            <div className="space-y-2">
              {rooms.map((room) => (
                <button
                  key={room.id}
                  onClick={() => selectRoom(room.id)}
                  className={`w-full text-left rounded px-2 py-2 text-sm border ${
                    selectedRoomId === room.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-800 bg-slate-900 hover:border-slate-700'
                  }`}
                >
                  <p className="font-medium">{room.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{room.status}</p>
                </button>
              ))}
              {!rooms.length && <p className="text-xs text-slate-500">No rooms yet.</p>}
            </div>
          </div>

          <RoomControls recruiterToken={recruiterToken} room={selectedRoom} />
        </aside>

        <main className="space-y-4">
          <section className="bg-slate-950 border border-slate-800 rounded-lg p-3">
            <h2 className="text-sm font-semibold mb-3">Candidates</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {candidates.map((candidate) => (
                <CandidateCard
                  key={candidate.id}
                  candidate={candidate}
                  selected={selectedCandidateId === candidate.id}
                  onSelect={() => {
                    selectCandidate(candidate.id)
                    if (selectedRoomId) markCandidateCheatRead(selectedRoomId, candidate.id)
                  }}
                />
              ))}
              {!candidates.length && <p className="text-sm text-slate-500">Waiting for candidates to join.</p>}
            </div>
          </section>

          <section className="bg-slate-950 border border-slate-800 rounded-lg p-3">
            {selectedRoomId ? (
              <CandidateLiveView
                roomId={selectedRoomId}
                candidate={selectedCandidate}
                recruiterToken={recruiterToken}
                events={candidateEvents}
              />
            ) : (
              <p className="text-sm text-slate-500">Select a room to monitor candidates.</p>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

