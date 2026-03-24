import { useSearchParams } from 'react-router-dom'
import { CodeEditor } from '../components/editor/CodeEditor'
import { LanguageSelector } from '../components/editor/LanguageSelector'
import { RunButton } from '../components/editor/RunButton'
import { TestResults } from '../components/editor/TestResults'
import { useExecution } from '../hooks/useExecution'

export function EditorPage() {
  const [params] = useSearchParams()
  const roomId = params.get('room') ?? 'demo-room'
  const candidateToken = params.get('token') ?? ''
  const attemptId = params.get('attempt') ?? 'demo-attempt'

  const { run, loading, result, error, cooldownSeconds } = useExecution({
    candidateToken,
    apiBaseUrl: 'http://127.0.0.1:8000',
  })

  return (
    <div className="modern-shell space-y-4">
      <div className="modern-card p-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Candidate Editor</h1>
        <div className="flex items-center gap-3">
          <LanguageSelector />
          <RunButton loading={loading} cooldownSeconds={cooldownSeconds} onRun={run} attemptId={attemptId} />
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-700 bg-rose-900/30 px-3 py-2 text-sm text-rose-200">{error}</div>}

      <CodeEditor roomId={roomId} candidateToken={candidateToken} wsBaseUrl="ws://127.0.0.1:1234/ws" />

      <TestResults result={result} />
    </div>
  )
}

