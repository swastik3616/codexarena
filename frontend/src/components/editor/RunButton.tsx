import { useEditorStore } from '../../store/editorStore'
import type { EditorLanguage } from '../../store/editorStore'

type Props = {
  loading: boolean
  cooldownSeconds: number
  onRun: (params: { attemptId: string; language: EditorLanguage; code: string }) => void
  attemptId: string
}

export const RunButton = ({ loading, cooldownSeconds, onRun, attemptId }: Props) => {
  const language = useEditorStore((s) => s.language)
  const code = useEditorStore((s) => s.code)

  const disabled = loading || cooldownSeconds > 0
  const label = loading ? 'Running...' : cooldownSeconds > 0 ? `Run again in ${cooldownSeconds}s` : 'Run'

  return (
    <button
      disabled={disabled}
      onClick={() => onRun({ attemptId, language, code })}
      className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium border ${
        disabled
          ? 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
          : 'bg-emerald-600 text-white border-emerald-500 hover:bg-emerald-500'
      }`}
    >
      {loading && <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />}
      {label}
    </button>
  )
}

