import { Link } from 'react-router-dom'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">CodexArena</h1>
        <p className="text-slate-400">Live coding interviews with real-time monitoring.</p>
        <div className="flex items-center justify-center gap-3">
          <Link to="/login" className="rounded bg-blue-600 hover:bg-blue-500 px-4 py-2 text-sm font-medium">
            Recruiter Login
          </Link>
        </div>
      </div>
    </div>
  )
}

