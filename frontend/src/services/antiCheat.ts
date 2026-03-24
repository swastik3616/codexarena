import type { editor as MonacoEditorNS } from 'monaco-editor'

type Severity = 'low' | 'medium' | 'high'

type EmitPayload = {
  event_type: 'large_paste' | 'keystroke_anomaly' | 'tab_switch' | 'copy_detected' | 'idle_timeout'
  severity: Severity
  payload: Record<string, unknown>
}

export class AntiCheatMonitor {
  private websocket: WebSocket | null = null
  private candidateId: string | null = null
  private editor: MonacoEditorNS.IStandaloneCodeEditor | null = null

  private keydownHandler: ((e: KeyboardEvent) => void) | null = null
  private visibilityHandler: (() => void) | null = null
  private copyHandler: ((e: ClipboardEvent) => void) | null = null
  private keyTimestamps: number[] = []
  private cadenceTimer: number | null = null
  private idleTimer: number | null = null
  private lastKeydownAt: number = Date.now()
  private pasteDisposable: { dispose: () => void } | null = null

  private emit(data: EmitPayload) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return
    this.websocket.send(
      JSON.stringify({
        type: 'cheat.event',
        event_type: data.event_type,
        severity: data.severity,
        payload: data.payload,
      }),
    )
  }

  monitorPaste(editor: MonacoEditorNS.IStandaloneCodeEditor) {
    this.editor = editor
    this.pasteDisposable = editor.onDidPaste((e) => {
      const text = e.range ? editor.getModel()?.getValueInRange(e.range) ?? '' : ''
      const count = text.length
      if (count > 50) {
        this.emit({
          event_type: 'large_paste',
          severity: count > 150 ? 'high' : 'low',
          payload: { char_count: count, timestamp: Date.now() },
        })
      }
    })
  }

  monitorKeystrokes() {
    this.keydownHandler = () => {
      const now = Date.now()
      this.keyTimestamps.push(now)
      if (this.keyTimestamps.length > 200) this.keyTimestamps.shift()
      this.lastKeydownAt = now
    }
    window.addEventListener('keydown', this.keydownHandler)

    this.cadenceTimer = window.setInterval(() => {
      if (this.keyTimestamps.length < 25) return
      const latest = this.keyTimestamps[this.keyTimestamps.length - 1]
      let burstCount = 0
      for (let i = this.keyTimestamps.length - 1; i >= 0; i--) {
        if (latest - this.keyTimestamps[i] <= 3000) burstCount += 1
        else break
      }
      // Gap before burst: last key before the burst window
      let priorIdx = this.keyTimestamps.length - burstCount - 1
      if (priorIdx < 0) return
      const prior = this.keyTimestamps[priorIdx]
      const gapSeconds = Math.floor((this.keyTimestamps[priorIdx + 1] - prior) / 1000)
      if (gapSeconds > 60 && burstCount > 20) {
        this.emit({
          event_type: 'keystroke_anomaly',
          severity: 'medium',
          payload: { gap_seconds: gapSeconds, burst_chars: burstCount },
        })
      }
    }, 10000)
  }

  monitorVisibility() {
    this.visibilityHandler = () => {
      if (document.visibilityState === 'hidden') {
        this.emit({
          event_type: 'tab_switch',
          severity: 'low',
          payload: { timestamp: Date.now() },
        })
      }
    }
    document.addEventListener('visibilitychange', this.visibilityHandler)
  }

  monitorCopy() {
    this.copyHandler = (e) => {
      const editor = this.editor
      if (!editor) return
      const model = editor.getModel()
      const selection = editor.getSelection()
      if (!model || !selection) return
      const selectedCode = model.getValueInRange(selection).trim()
      if (!selectedCode) return
      this.emit({
        event_type: 'copy_detected',
        severity: 'medium',
        payload: { char_count: selectedCode.length },
      })
      if (e.clipboardData && selectedCode) {
        e.clipboardData.setData('text/plain', selectedCode)
      }
    }
    document.addEventListener('copy', this.copyHandler)
  }

  monitorIdle() {
    this.idleTimer = window.setInterval(() => {
      const idleSeconds = Math.floor((Date.now() - this.lastKeydownAt) / 1000)
      if (idleSeconds >= 180) {
        this.emit({
          event_type: 'idle_timeout',
          severity: 'low',
          payload: { idle_seconds: 180 },
        })
        // Reset baseline to avoid repeated spam every interval.
        this.lastKeydownAt = Date.now()
      }
    }, 10000)
  }

  startAll(
    websocket: WebSocket,
    candidateId: string,
    editor: MonacoEditorNS.IStandaloneCodeEditor | null,
  ) {
    this.websocket = websocket
    this.candidateId = candidateId
    this.lastKeydownAt = Date.now()
    if (editor) this.monitorPaste(editor)
    this.monitorKeystrokes()
    this.monitorVisibility()
    this.monitorCopy()
    this.monitorIdle()
  }

  stopAll() {
    if (this.keydownHandler) window.removeEventListener('keydown', this.keydownHandler)
    if (this.visibilityHandler) document.removeEventListener('visibilitychange', this.visibilityHandler)
    if (this.copyHandler) document.removeEventListener('copy', this.copyHandler)
    if (this.cadenceTimer) window.clearInterval(this.cadenceTimer)
    if (this.idleTimer) window.clearInterval(this.idleTimer)
    this.pasteDisposable?.dispose()
    this.keydownHandler = null
    this.visibilityHandler = null
    this.copyHandler = null
    this.cadenceTimer = null
    this.idleTimer = null
    this.pasteDisposable = null
    this.websocket = null
    this.candidateId = null
    this.editor = null
    this.keyTimestamps = []
  }
}

