import { useEffect, useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import type { editor as MonacoEditorNS } from 'monaco-editor'
import { CodeEditor } from '../components/editor/CodeEditor'
import { LanguageSelector } from '../components/editor/LanguageSelector'
import { RunButton } from '../components/editor/RunButton'
import { TestResults } from '../components/editor/TestResults'
import { useExecution } from '../hooks/useExecution'
import { getCandidateSession, type InterviewQuestion, setCandidateSession } from '../lib/candidateSession'
import { QuestionPanel } from '../components/candidate/QuestionPanel'
import { AntiCheatMonitor } from '../services/antiCheat'
import { FaceDetectionMonitor, type CameraState } from '../services/faceDetection'
import { CameraStatus } from '../components/candidate/CameraStatus'

export function CandidateInterview() {
  const { room_id } = useParams<{ room_id: string }>()
  const session = getCandidateSession()
  const [question, setQuestion] = useState<InterviewQuestion | null>(session?.question ?? null)
  const attemptId = session?.attemptId ?? ''
  const [editorRef, setEditorRef] = useState<MonacoEditorNS.IStandaloneCodeEditor | null>(null)
  const [cameraState, setCameraState] = useState<CameraState>('idle')
  const [cameraMessage, setCameraMessage] = useState<string | undefined>(undefined)

  const { run, loading, result, error, cooldownSeconds } = useExecution({
    candidateToken: session?.candidateToken,
    apiBaseUrl: 'http://127.0.0.1:8000',
  })

  const wsUrl = useMemo(() => {
    if (!room_id || !session?.candidateToken) return null
    return `ws://127.0.0.1:8000/ws/${room_id}?token=${encodeURIComponent(session.candidateToken)}`
  }, [room_id, session?.candidateToken])

  useEffect(() => {
    if (!wsUrl || !session?.candidateId) return
    const ws = new WebSocket(wsUrl)
    const antiCheat = new AntiCheatMonitor()
    let faceMonitor: FaceDetectionMonitor | null = null
    ws.onopen = () => {
      antiCheat.startAll(ws, session.candidateId, editorRef)
      faceMonitor = new FaceDetectionMonitor(ws, (state, message) => {
        setCameraState(state)
        setCameraMessage(message)
      })
      void faceMonitor.init()
    }
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'room.joined' && msg.candidate?.id === session.candidateId && msg.question) {
          setQuestion(msg.question as InterviewQuestion)
          setCandidateSession({ ...session, question: msg.question })
        }
      } catch {
        // ignore malformed
      }
    }
    return () => {
      antiCheat.stopAll()
      faceMonitor?.stop()
      ws.close()
    }
  }, [wsUrl, session, editorRef])

  if (!room_id || !session || session.roomId !== room_id) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="grid grid-cols-1 xl:grid-cols-[40%_60%] gap-4">
        <QuestionPanel question={question} />

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">Candidate Interview</h1>
            <div className="flex items-center gap-2">
            <CameraStatus state={cameraState} message={cameraMessage} />
              <LanguageSelector />
              <RunButton
                loading={loading}
                cooldownSeconds={cooldownSeconds}
                attemptId={attemptId}
                onRun={run}
              />
            </div>
          </div>
          {error && <div className="rounded border border-rose-700 bg-rose-900/30 px-3 py-2 text-sm text-rose-200">{error}</div>}
          <CodeEditor
            roomId={room_id}
            candidateToken={session.candidateToken}
            wsBaseUrl="ws://127.0.0.1:1234/ws"
            onEditorReady={setEditorRef}
          />
          <TestResults result={result} />
        </section>
      </div>
    </div>
  )
}

