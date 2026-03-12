import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const MainLayout = () => {
  return (
    <div className="flex min-h-screen bg-slate-50/50 font-sans selection:bg-blue-100 selection:text-blue-900">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
