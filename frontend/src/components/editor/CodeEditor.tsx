import { useEffect, useMemo, useRef, useState } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { MonacoBinding } from 'y-monaco'
import type { editor as MonacoEditorNS } from 'monaco-editor'
import { useEditorStore, type EditorLanguage } from '../../store/editorStore'

type Props = {
  roomId: string
  candidateToken?: string
  wsBaseUrl?: string
}

type ConnectionStatus = 'connected' | 'reconnecting' | 'offline'

const statusMeta: Record<ConnectionStatus, { label: string; cls: string }> = {
  connected: { label: 'Connected', cls: 'bg-emerald-500' },
  reconnecting: { label: 'Reconnecting', cls: 'bg-amber-500' },
  offline: { label: 'Offline', cls: 'bg-rose-500' },
}

export const CodeEditor = ({ roomId, candidateToken, wsBaseUrl = 'ws://127.0.0.1:1234/ws' }: Props) => {
  const language = useEditorStore((s) => s.language)
  const code = useEditorStore((s) => s.code)
  const setCode = useEditorStore((s) => s.setCode)

  const editorRef = useRef<MonacoEditorNS.IStandaloneCodeEditor | null>(null)
  const ydocRef = useRef<Y.Doc | null>(null)
  const providerRef = useRef<WebsocketProvider | null>(null)
  const bindingRef = useRef<MonacoBinding | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('reconnecting')

  const params = useMemo(() => {
    const p: Record<string, string> = {}
    if (candidateToken) p.token = candidateToken
    return p
  }, [candidateToken])

  const onMount: OnMount = (editor) => {
    editorRef.current = editor

    const model = editor.getModel()
    if (!model) return

    const ydoc = new Y.Doc()
    ydocRef.current = ydoc

    const provider = new WebsocketProvider(wsBaseUrl, roomId, ydoc, { params })
    providerRef.current = provider

    const ytext = ydoc.getText('monaco')
    // seed editor text once if no shared state exists yet
    if (ytext.length === 0 && code.length > 0) {
      ytext.insert(0, code)
    }

    const binding = new MonacoBinding(ytext, model, new Set([editor]), provider.awareness)
    bindingRef.current = binding

    provider.on('status', (event: { status: 'connected' | 'disconnected' | 'connecting' }) => {
      if (event.status === 'connected') {
        if (reconnectTimerRef.current) {
          window.clearTimeout(reconnectTimerRef.current)
          reconnectTimerRef.current = null
        }
        setConnectionStatus('connected')
      } else if (event.status === 'connecting') {
        setConnectionStatus('reconnecting')
      } else {
        setConnectionStatus('reconnecting')
        if (reconnectTimerRef.current) {
          window.clearTimeout(reconnectTimerRef.current)
        }
        reconnectTimerRef.current = window.setTimeout(() => {
          setConnectionStatus('offline')
        }, 4000)
      }
    })
  }

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current)
      bindingRef.current?.destroy()
      providerRef.current?.destroy()
      ydocRef.current?.destroy()
    }
  }, [])

  const status = statusMeta[connectionStatus]

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-950">
        <span className="text-sm text-slate-300">Collaborative Editor</span>
        <span className="inline-flex items-center gap-2 text-xs text-slate-200">
          <span className={`inline-block h-2 w-2 rounded-full ${status.cls}`} />
          {status.label}
        </span>
      </div>

      <Editor
        height="420px"
        language={language}
        value={code}
        theme="vs-dark"
        onMount={onMount}
        onChange={(value) => setCode(value ?? '')}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          automaticLayout: true,
        }}
      />
    </section>
  )
}

