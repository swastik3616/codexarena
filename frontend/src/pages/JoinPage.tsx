import { useParams } from 'react-router-dom'

export function JoinPage() {
  const { roomId } = useParams<{ roomId: string }>()
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold">Join room {roomId}</h1>
      <p className="mt-2 text-slate-600">Candidate join placeholder.</p>
    </div>
  )
}

