import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { RoomsPage } from './pages/RoomsPage'
import { RoomDetailPage } from './pages/RoomDetailPage'
import { JoinPage } from './pages/JoinPage'
import { EditorPage } from './pages/EditorPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/rooms" element={<RoomsPage />} />
      <Route path="/rooms/:roomId" element={<RoomDetailPage />} />
      <Route path="/join/:roomId" element={<JoinPage />} />
      <Route path="/editor" element={<EditorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

