import type { ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { LandingPage } from './pages/LandingPage'
import { RecruiterLogin } from './pages/RecruiterLogin'
import { RecruiterDashboard } from './pages/RecruiterDashboard'
import { JoinRoom } from './pages/JoinRoom'
import { WaitingRoom } from './pages/WaitingRoom'
import { CandidateInterview } from './pages/CandidateInterview'
import { EvaluationReport } from './pages/EvaluationReport'

function ProtectedRecruiterRoute({ children }: { children: ReactElement }) {
  const token = localStorage.getItem('recruiterToken')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<RecruiterLogin />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRecruiterRoute>
            <RecruiterDashboard />
          </ProtectedRecruiterRoute>
        }
      />
      <Route
        path="/report/:attempt_id"
        element={
          <ProtectedRecruiterRoute>
            <EvaluationReport />
          </ProtectedRecruiterRoute>
        }
      />
      <Route path="/join/:token" element={<JoinRoom />} />
      <Route path="/waiting/:room_id" element={<WaitingRoom />} />
      <Route path="/interview/:room_id" element={<CandidateInterview />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

