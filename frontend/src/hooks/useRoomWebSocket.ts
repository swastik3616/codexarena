import { useEffect, useRef } from 'react'
import { useRoomStore } from '../store/roomStore'

type Params = {
  roomId: string | null
  recruiterToken?: string
  wsBase?: string
}

export const useRoomWebSocket = ({ roomId, recruiterToken, wsBase = 'ws://127.0.0.1:8000/ws' }: Params) => {
  const upsertCandidate = useRoomStore((s) => s.upsertCandidate)
  const updateCandidateCursor = useRoomStore((s) => s.updateCandidateCursor)
  const updateExecution = useRoomStore((s) => s.updateExecution)
  const pushCheatEvent = useRoomStore((s) => s.pushCheatEvent)

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!roomId || !recruiterToken) return

    const ws = new WebSocket(`${wsBase}/${roomId}?token=${encodeURIComponent(recruiterToken)}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const type = msg?.type

        if (type === 'room.joined') {
          const c = msg.candidate
          upsertCandidate(roomId, {
            id: String(c.id),
            name: String(c.name ?? 'Candidate'),
            status: c.status ?? 'waiting',
          })
        } else if (type === 'cursor.update') {
          updateCandidateCursor(roomId, String(msg.candidate_id), {
            line: Number(msg.position?.line ?? 1),
            column: Number(msg.position?.column ?? 1),
          })
        } else if (type === 'execution.result' || type === 'ai.evaluation') {
          updateExecution(roomId, String(msg.candidate_id), {
            pass_count: Number(msg.pass_count ?? msg.result?.pass_count ?? 0),
            total: Number(msg.total ?? msg.result?.total ?? 0),
            timed_out: Boolean(msg.timed_out ?? msg.result?.timed_out ?? false),
          })
        } else if (type === 'cheat.event') {
          pushCheatEvent(roomId, {
            id: `${Date.now()}-${Math.random()}`,
            candidateId: String(msg.candidate_id),
            severity: (String(msg.severity ?? 'LOW').toUpperCase() as 'LOW' | 'MEDIUM' | 'HIGH'),
            eventType: String(msg.event_type ?? 'unknown'),
            timestamp: Date.now(),
          })
        }
      } catch {
        // ignore malformed events
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [roomId, recruiterToken, wsBase, upsertCandidate, updateCandidateCursor, updateExecution, pushCheatEvent])
}

