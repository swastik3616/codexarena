import { useState } from 'react'
import axios from 'axios'
import type { RoomState } from '../../store/roomStore'
import { useRoomStore } from '../../store/roomStore'

type Props = {
  recruiterToken?: string
  room: RoomState | null
  apiBase?: string
}

export const RoomControls = ({ recruiterToken, room, apiBase = 'http://127.0.0.1:8000' }: Props) => {
  const upsertRoom = useRoomStore((s) => s.upsertRoom)
  const [title, setTitle] = useState('')
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [copied, setCopied] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const authHeaders = recruiterToken
    ? { Authorization: `Bearer ${recruiterToken}`, 'Content-Type': 'application/json' }
    : undefined

  const createRoom = async () => {
    if (!title.trim() || !recruiterToken) return
    setSubmitting(true)
    try {
      const res = await axios.post(
        `${apiBase}/rooms`,
        { title: title.trim(), difficulty },
        {
          headers: authHeaders,
        },
      )
      upsertRoom({
        id: res.data.room_id,
        title: res.data.title,
        difficulty,
        status: res.data.status,
        joinLink: res.data.join_link,
      })
      setTitle('')
    } finally {
      setSubmitting(false)
    }
  }

  const copyJoinLink = async () => {
    if (!room?.joinLink) return
    await navigator.clipboard.writeText(room.joinLink)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  const closeRoom = async () => {
    if (!room || !recruiterToken) return
    await axios.delete(`${apiBase}/rooms/${room.id}`, {
      headers: recruiterToken
        ? { Authorization: `Bearer ${recruiterToken}`, 'Content-Type': 'application/json' }
        : undefined,
    })
    upsertRoom({ ...room, status: 'completed' })
  }

  return (
    <section className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-3">
      <h3 className="text-sm font-semibold text-slate-200">Room Controls</h3>

      <div className="space-y-2">
        <input
          placeholder="Room title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded bg-slate-900 border border-slate-800 px-2 py-1.5 text-sm text-slate-200"
        />
        <select
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
          className="w-full rounded bg-slate-900 border border-slate-800 px-2 py-1.5 text-sm text-slate-200"
        >
          <option value="easy">easy</option>
          <option value="medium">medium</option>
          <option value="hard">hard</option>
        </select>
        <button
          onClick={createRoom}
          disabled={submitting || !recruiterToken}
          className="w-full rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-2 text-sm font-medium"
        >
          {submitting ? 'Creating...' : 'Create room'}
        </button>
      </div>

      {room && (
        <div className="space-y-2 border-t border-slate-800 pt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Status</span>
            <span className="rounded px-2 py-0.5 bg-slate-800 text-slate-200">{room.status}</span>
          </div>
          <button
            onClick={copyJoinLink}
            disabled={!room.joinLink}
            className="w-full rounded bg-slate-800 hover:bg-slate-700 px-3 py-2 text-sm text-slate-100"
          >
            {copied ? 'Copied!' : 'Copy join link'}
          </button>
          <button
            onClick={closeRoom}
            className="w-full rounded bg-rose-700/80 hover:bg-rose-700 px-3 py-2 text-sm text-white"
          >
            Close room
          </button>
        </div>
      )}
    </section>
  )
}

