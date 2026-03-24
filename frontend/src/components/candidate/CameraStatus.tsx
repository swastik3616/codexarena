import type { CameraState } from '../../services/faceDetection'

type Props = {
  state: CameraState
  message?: string
}

const clsByState: Record<CameraState, string> = {
  active: 'bg-emerald-500',
  denied: 'bg-slate-500',
  error: 'bg-rose-500',
  idle: 'bg-slate-700',
}

const labelByState: Record<CameraState, string> = {
  active: 'Active',
  denied: 'Denied',
  error: 'Error',
  idle: 'Idle',
}

export function CameraStatus({ state, message }: Props) {
  const tooltip =
    state === 'active'
      ? 'Camera monitoring is active for this interview'
      : message ?? 'Camera access recommended for this interview'

  return (
    <div className="inline-flex items-center gap-2 rounded border border-slate-800 bg-slate-900 px-2 py-1" title={tooltip}>
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${clsByState[state]}`} />
      <span className="text-xs text-slate-200">Camera {labelByState[state]}</span>
    </div>
  )
}

