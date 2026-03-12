import { useState } from 'react'
import { Users, Search, Filter, Plus, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export const RoomsPage = () => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const navigate = useNavigate()

  const handleCreateRoom = (e: React.FormEvent) => {
    e.preventDefault()
    const roomId = 'room' + Math.floor(Math.random() * 10000)
    navigate(`/rooms/${roomId}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Interview Rooms</h2>
          <p className="text-slate-500 mt-1">Manage and create technical interview sessions.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-all duration-200 shadow-sm shadow-blue-200 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create Room
        </button>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-5 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800">Create New Room</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateRoom} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Room Name</label>
                <input type="text" required placeholder="e.g. Senior Frontend Role" className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-400 outline-none" />
              </div>
              <div className="pt-2">
                <button type="submit" className="w-full bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 transition-colors">
                  Generate Room Link
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search rooms..." 
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all"
          />
        </div>
        <button className="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 flex items-center gap-2 hover:bg-slate-50 transition-colors">
          <Filter className="w-5 h-5" />
          Filters
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 lg:gap-6">
        {/* Dummy Active Room for Testing */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-xl font-bold text-slate-800">Demo Interview Room</h3>
              <p className="text-sm text-slate-500 font-mono mt-1">ID: room123</p>
            </div>
            <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Active
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-6 mt-2">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
              <p className="text-slate-500 text-xs font-medium mb-1">Candidates</p>
              <p className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-500" />
                Live Sync
              </p>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
              <p className="text-slate-500 text-xs font-medium mb-1">Duration</p>
              <p className="text-xl font-bold text-slate-800">45m</p>
            </div>
          </div>

          <a href="/rooms/room123" className="mt-auto w-full py-2.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-xl font-medium text-center transition-colors border border-blue-200 block">
            Monitor Room
          </a>
        </div>
      </div>
    </div>
  )
}
