import { Link } from 'react-router-dom'

export function LandingPage() {
  return (
    <div className="modern-shell flex items-center justify-center">
      <div className="modern-card w-full max-w-2xl p-8 text-center space-y-5">
        <h1 className="modern-title">CodexArena</h1>
        <p className="modern-muted">Real-time coding interviews with AI evaluation and live recruiter insights.</p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link to="/login" className="modern-btn-primary">
            Recruiter Login
          </Link>
        </div>
      </div>
    </div>
  )
}

