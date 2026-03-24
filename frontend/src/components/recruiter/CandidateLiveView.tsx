import { useEffect, useMemo, useRef } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { MonacoBinding } from 'y-monaco'
import type { editor as MonacoEditorNS } from 'monaco-editor'
import type { CandidateRoomState, CheatEvent } from '../../store/roomStore'
import { CheatAlertPanel } from './CheatAlertPanel'

type Props = {
  roomId: string
  candidate: CandidateRoomState | null
  recruiterToken?: string
  wsBaseUrl?: string
  events: CheatEvent[]
}

export const CandidateLiveView = ({
  roomId,
  candidate,
  recruiterToken,
  wsBaseUrl = 'ws://127.0.0.1:1234/ws',
  events,
}: Props) => {
  const editorRef = useRef<MonacoEditorNS.IStandaloneCodeEditor | null>(null)
  const ydocRef = useRef<Y.Doc | null>(null)
  const providerRef = useRef<WebsocketProvider | null>(null)
  const bindingRef = useRef<MonacoBinding | null>(null)

  const params = useMemo<Record<string, string>>(() => {
    const p: Record<string, string> = {}
    if (recruiterToken) p.token = recruiterToken
    p.role = 'viewer'
    if (candidate) p.watching = candidate.id
    return p
  }, [recruiterToken, candidate])

  const onMount: OnMount = (editor) => {
    editorRef.current = editor
    const model = editor.getModel()
    if (!model || !candidate) return

    const ydoc = new Y.Doc()
    ydocRef.current = ydoc
    const provider = new WebsocketProvider(wsBaseUrl, roomId, ydoc, { params })
    providerRef.current = provider
    const ytext = ydoc.getText('monaco')
    const binding = new MonacoBinding(ytext, model, new Set([editor]), provider.awareness)
    bindingRef.current = binding
  }

  useEffect(() => {
    return () => {
      bindingRef.current?.destroy()
      providerRef.current?.destroy()
      ydocRef.current?.destroy()
    }
  }, [])

  if (!candidate) {
    return <div className="text-sm text-slate-400">Select a candidate to open live view.</div>
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-slate-100">{candidate.name} — Live View</h3>
        {candidate.cursor && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-300">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            L{candidate.cursor.line}:C{candidate.cursor.column}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
        <Editor
          height="420px"
          defaultLanguage="python"
          theme="vs-dark"
          value=""
          onMount={onMount}
          options={{ readOnly: true, minimap: { enabled: false }, automaticLayout: true, fontSize: 13 }}
        />

        <aside className="space-y-3">
          <section className="bg-slate-950 border border-slate-800 rounded-lg p-3">
            <h4 className="text-sm font-semibold text-slate-200 mb-2">Execution</h4>
            {candidate.execution ? (
              <p className="text-sm text-slate-300">
                {candidate.execution.pass_count} / {candidate.execution.total} passed
              </p>
            ) : (
              <p className="text-sm text-slate-500">No execution result yet.</p>
            )}
          </section>
          <CheatAlertPanel events={events} />
        </aside>
      </div>
    </div>
  )
}

