import { Activity, Users, Star, Clock } from 'lucide-react'

const StatCard = ({ title, value, icon: Icon, trend, trendValue }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-200">
    <div className="flex items-center justify-between mb-4">
      <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600">
        <Icon className="w-5 h-5" />
      </div>
      {trend && (
        <span className={`text-sm font-medium ${trend === 'up' ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50'} px-2 py-1 rounded-full`}>
          {trend === 'up' ? '+' : ''}{trendValue}%
        </span>
      )}
    </div>
    <div>
      <h3 className="text-slate-500 font-medium mb-1 text-sm">{title}</h3>
      <p className="text-3xl font-bold text-slate-800 tracking-tight">{value}</p>
    </div>
  </div>
)

export const DashboardPage = () => {
  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Overview</h2>
        <p className="text-slate-500 mt-1">Here's what's happening in your interview sessions today.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Active Interviews" value="12" icon={Activity} trend="up" trendValue="14" />
        <StatCard title="Total Candidates" value="148" icon={Users} trend="up" trendValue="8" />
        <StatCard title="Average Score" value="86.4" icon={Star} trend="up" trendValue="2" />
        <StatCard title="Time Spent" value="45m" icon={Clock} trend="down" trendValue="12" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 p-6 min-h-[400px]">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Recent Submissions</h3>
          {/* Placeholder for chart/table */}
          <div className="h-full flex items-center justify-center text-slate-400 border-2 border-dashed border-slate-100 rounded-xl">
            Activity Graph Area
          </div>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Upcoming Interviews</h3>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4 p-3 hover:bg-slate-50 rounded-xl transition-colors cursor-pointer">
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-medium">
                  CA
                </div>
                <div>
                  <p className="font-medium text-slate-800 text-sm">Candidate {i}</p>
                  <p className="text-slate-500 text-xs">Python Developer • In 2 hours</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
