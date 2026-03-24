import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const API_BASE = 'http://127.0.0.1:8000'

export function RecruiterLogin() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const login = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post(`${API_BASE}/auth/login`, { email, password })
      localStorage.setItem('recruiterToken', res.data.access_token)
      navigate('/dashboard')
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modern-shell flex items-center justify-center">
      <div className="modern-card w-full max-w-md p-6">
        <h1 className="modern-title text-xl">Recruiter Login</h1>
        <input
          className="mt-4 w-full rounded-xl bg-slate-950/70 border border-white/10 px-3 py-2.5 text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="mt-2 w-full rounded-xl bg-slate-950/70 border border-white/10 px-3 py-2.5 text-sm"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        <button
          onClick={login}
          disabled={loading || !email || !password}
          className="modern-btn-primary mt-4 w-full disabled:opacity-50"
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </div>
    </div>
  )
}

