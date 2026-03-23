import type { EditorLanguage } from '../../store/editorStore'
import { useEditorStore } from '../../store/editorStore'

const OPTIONS: Array<{ value: EditorLanguage; label: string }> = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' },
]

export const LanguageSelector = () => {
  const language = useEditorStore((s) => s.language)
  const setLanguage = useEditorStore((s) => s.setLanguage)

  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <span className="text-slate-400">Language</span>
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value as EditorLanguage)}
        className="rounded-md bg-slate-800 text-slate-100 border border-slate-700 px-2 py-1"
      >
        {OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  )
}

