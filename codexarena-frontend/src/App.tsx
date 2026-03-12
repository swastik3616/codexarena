import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MainLayout } from './components/MainLayout'
import { DashboardPage } from './pages/DashboardPage'
import { RoomsPage } from './pages/RoomsPage'
import { EditorPage } from './pages/EditorPage'
import { JoinPage } from './pages/JoinPage'
import { RoomDetailPage } from './pages/RoomDetailPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Recruiter Routes (With Sidebar) */}
        <Route element={<MainLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/rooms/:roomId" element={<RoomDetailPage />} />
        </Route>

        {/* Candidate Routes (Standalone/Fullscreen) */}
        <Route path="/join/:roomId" element={<JoinPage />} />
        <Route path="/editor" element={<EditorPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App