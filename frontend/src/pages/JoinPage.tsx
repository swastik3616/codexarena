import { useParams } from 'react-router-dom'

export function JoinPage() {
  const { roomId } = useParams<{ roomId: string }>()
  return (
    <div className="modern-shell flex items-center justify-center">
      <div className="modern-card p-8 text-center">
        <h1 className="modern-title text-xl">Join room {roomId}</h1>
        <p className="modern-muted mt-2">Candidate join placeholder.</p>
      </div>
    </div>
  )
}

