import { useParams } from 'react-router-dom'

export function RoomDetailPage() {
  const { roomId } = useParams<{ roomId: string }>()
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold">Room {roomId}</h1>
      <p className="mt-2 text-slate-600">Live monitoring placeholder.</p>
    </div>
  )
}

