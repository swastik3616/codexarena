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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-lg p-5">
        <h1 className="text-xl font-semibold">Recruiter Login</h1>
        <input
          className="mt-4 w-full rounded bg-slate-950 border border-slate-800 px-3 py-2 text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="mt-2 w-full rounded bg-slate-950 border border-slate-800 px-3 py-2 text-sm"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        <button
          onClick={login}
          disabled={loading || !email || !password}
          className="mt-4 w-full rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-2 text-sm font-medium"
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </div>
    </div>
  )
}

