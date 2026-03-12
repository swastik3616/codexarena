import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Code, ArrowRight, ShieldCheck } from 'lucide-react'

export const JoinPage = () => {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault()
    // In the future, this will authenticate with the backend and establish a WebSocket connection.
    // For now, we simulate joining and redirecting to the editor.
    navigate(`/editor?room=${roomId}&candidate=${encodeURIComponent(name)}`)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-sans selection:bg-blue-100 selection:text-blue-900">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-6">
            <Code className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Join Interview</h1>
          <p className="text-slate-500">You've been invited to a CodexArena coding session.</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8">
          <form onSubmit={handleJoin} className="space-y-5">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all font-medium text-slate-800 placeholder:text-slate-400 placeholder:font-normal"
                placeholder="John Doe"
              />
            </div>
            
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">Email Address</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all font-medium text-slate-800 placeholder:text-slate-400 placeholder:font-normal"
                placeholder="john@example.com"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3.5 rounded-xl font-medium transition-all duration-200 shadow-sm shadow-blue-200 flex items-center justify-center gap-2 group"
              >
                Join Session
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </form>

          <div className="mt-6 flex items-start gap-3 bg-blue-50/50 p-4 rounded-xl border border-blue-100/50">
            <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
            <p className="text-sm text-slate-600 leading-relaxed">
              This is a proctored environment. By joining, you agree to camera and tab-switching monitoring logic.
            </p>
          </div>
        </div>

        <p className="text-center text-slate-400 text-sm mt-8">
          Powered by <span className="font-semibold text-slate-500">CodexArena</span>
        </p>
      </div>
    </div>
  )
}
