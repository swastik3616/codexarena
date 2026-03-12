import { LayoutDashboard, Users, Code, Settings, LogOut } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '../lib/utils'

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Interview Rooms', href: '/rooms', icon: Users },
  { name: 'Sandbox', href: '/editor', icon: Code },
]

export const Sidebar = () => {
  const location = useLocation()

  return (
    <aside className="w-64 bg-white border-r border-slate-200 h-screen sticky top-0 flex flex-col font-sans">
      <div className="p-6 border-b border-slate-100 flex items-center justify-center">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent tracking-tight">
          CodexArena
        </h1>
      </div>
      <nav className="p-4 flex-1 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200",
                isActive 
                  ? "bg-blue-50/80 text-blue-700 shadow-sm shadow-blue-100/50" 
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-blue-600" : "text-slate-400")} />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t border-slate-100 space-y-1.5">
        <button className="flex w-full items-center space-x-3 px-4 py-3 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium transition-colors">
          <Settings className="w-5 h-5 text-slate-400" />
          <span>Settings</span>
        </button>
        <button className="flex w-full items-center space-x-3 px-4 py-3 text-slate-500 hover:bg-red-50 hover:text-red-700 rounded-xl font-medium transition-colors">
          <LogOut className="w-5 h-5 text-slate-400 group-hover:text-red-600" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
