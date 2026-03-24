import { create } from 'zustand'

export type CandidateStatus = 'waiting' | 'coding' | 'submitted' | 'evaluated'

export type ExecutionSummary = {
  pass_count: number
  total: number
  timed_out?: boolean
}

export type CheatEvent = {
  id: string
  candidateId: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH'
  eventType: string
  timestamp: number
}

export type CandidateRoomState = {
  id: string
  name: string
  status: CandidateStatus
  cursor?: { line: number; column: number }
  execution?: ExecutionSummary
  unreadCheatCount: number
}

export type RoomState = {
  id: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  status: string
  joinLink?: string
}

type StoreState = {
  rooms: RoomState[]
  selectedRoomId: string | null
  selectedCandidateId: string | null
  candidatesByRoom: Record<string, CandidateRoomState[]>
  cheatEventsByRoom: Record<string, CheatEvent[]>

  setRooms: (rooms: RoomState[]) => void
  upsertRoom: (room: RoomState) => void
  selectRoom: (roomId: string | null) => void
  selectCandidate: (candidateId: string | null) => void
  upsertCandidate: (roomId: string, candidate: Omit<CandidateRoomState, 'unreadCheatCount'>) => void
  updateCandidateCursor: (roomId: string, candidateId: string, cursor: { line: number; column: number }) => void
  updateExecution: (roomId: string, candidateId: string, execution: ExecutionSummary) => void
  pushCheatEvent: (roomId: string, event: CheatEvent) => void
  markCandidateCheatRead: (roomId: string, candidateId: string) => void
}

export const useRoomStore = create<StoreState>((set, get) => ({
  rooms: [],
  selectedRoomId: null,
  selectedCandidateId: null,
  candidatesByRoom: {},
  cheatEventsByRoom: {},

  setRooms: (rooms) => set({ rooms }),
  upsertRoom: (room) =>
    set((state) => {
      const idx = state.rooms.findIndex((r) => r.id === room.id)
      if (idx === -1) return { rooms: [room, ...state.rooms] }
      const copy = [...state.rooms]
      copy[idx] = { ...copy[idx], ...room }
      return { rooms: copy }
    }),
  selectRoom: (roomId) => set({ selectedRoomId: roomId, selectedCandidateId: null }),
  selectCandidate: (candidateId) => set({ selectedCandidateId: candidateId }),

  upsertCandidate: (roomId, candidate) =>
    set((state) => {
      const list = state.candidatesByRoom[roomId] ?? []
      const idx = list.findIndex((c) => c.id === candidate.id)
      let next: CandidateRoomState[]
      if (idx === -1) {
        next = [...list, { ...candidate, unreadCheatCount: 0 }]
      } else {
        next = [...list]
        next[idx] = { ...next[idx], ...candidate }
      }
      return { candidatesByRoom: { ...state.candidatesByRoom, [roomId]: next } }
    }),

  updateCandidateCursor: (roomId, candidateId, cursor) =>
    set((state) => {
      const list = state.candidatesByRoom[roomId] ?? []
      const next = list.map((c) => (c.id === candidateId ? { ...c, cursor } : c))
      return { candidatesByRoom: { ...state.candidatesByRoom, [roomId]: next } }
    }),

  updateExecution: (roomId, candidateId, execution) =>
    set((state) => {
      const list = state.candidatesByRoom[roomId] ?? []
      const next = list.map((c) => (c.id === candidateId ? { ...c, execution } : c))
      return { candidatesByRoom: { ...state.candidatesByRoom, [roomId]: next } }
    }),

  pushCheatEvent: (roomId, event) =>
    set((state) => {
      const events = state.cheatEventsByRoom[roomId] ?? []
      const candidates = state.candidatesByRoom[roomId] ?? []
      const updatedCandidates = candidates.map((c) =>
        c.id === event.candidateId ? { ...c, unreadCheatCount: c.unreadCheatCount + 1 } : c,
      )
      return {
        cheatEventsByRoom: { ...state.cheatEventsByRoom, [roomId]: [...events, event] },
        candidatesByRoom: { ...state.candidatesByRoom, [roomId]: updatedCandidates },
      }
    }),

  markCandidateCheatRead: (roomId, candidateId) =>
    set((state) => {
      const list = state.candidatesByRoom[roomId] ?? []
      const next = list.map((c) => (c.id === candidateId ? { ...c, unreadCheatCount: 0 } : c))
      return { candidatesByRoom: { ...state.candidatesByRoom, [roomId]: next } }
    }),
}))

