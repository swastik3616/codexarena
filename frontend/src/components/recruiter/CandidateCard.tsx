import type { CandidateRoomState } from '../../store/roomStore'

type Props = {
  candidate: CandidateRoomState
  selected: boolean
  onSelect: () => void
}

const statusClass: Record<CandidateRoomState['status'], string> = {
  waiting: 'bg-slate-700 text-slate-200',
  coding: 'bg-blue-600/30 text-blue-300 border border-blue-500/30',
  submitted: 'bg-amber-600/30 text-amber-300 border border-amber-500/30',
  evaluated: 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30',
}

export const CandidateCard = ({ candidate, selected, onSelect }: Props) => {
  const highRisk = candidate.unreadCheatCount > 0
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left rounded-lg border p-3 transition ${
        selected ? 'border-blue-500 bg-blue-500/10' : 'border-slate-800 bg-slate-900 hover:border-slate-700'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-100">{candidate.name}</p>
        <span className={`text-[10px] rounded px-2 py-0.5 ${statusClass[candidate.status]}`}>{candidate.status}</span>
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs">
        {candidate.execution ? (
          <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-200">
            {candidate.execution.pass_count}/{candidate.execution.total}
          </span>
        ) : (
          <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-400">No run yet</span>
        )}

        <span
          className={`rounded px-2 py-0.5 ${
            highRisk ? 'bg-rose-600/30 text-rose-300 border border-rose-500/30' : 'bg-slate-800 text-slate-400'
          }`}
        >
          Cheats: {candidate.unreadCheatCount}
        </span>
      </div>
    </button>
  )
}

