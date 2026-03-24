import { FaceMesh } from '@mediapipe/face_mesh'

export type CameraState = 'active' | 'denied' | 'error' | 'idle'

type StatusListener = (state: CameraState, message?: string) => void

export class FaceDetectionMonitor {
  private websocket: WebSocket | null = null
  private stream: MediaStream | null = null
  private videoEl: HTMLVideoElement | null = null
  private faceMesh: FaceMesh | null = null
  private intervalId: number | null = null
  private absentStartedAt: number | null = null
  private statusListener: StatusListener | null = null
  private lastResultCount = 0
  private busy = false

  constructor(ws: WebSocket, onStatus?: StatusListener) {
    this.websocket = ws
    this.statusListener = onStatus ?? null
  }

  private emit(event_type: 'face_absent' | 'multi_face', severity: 'high', payload: Record<string, unknown>) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return
    this.websocket.send(JSON.stringify({ type: 'cheat.event', event_type, severity, payload }))
  }

  async init() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video: true })
    } catch {
      this.handlePermissionDenied()
      return
    }

    this.videoEl = document.createElement('video')
    this.videoEl.style.display = 'none'
    this.videoEl.setAttribute('playsinline', 'true')
    this.videoEl.muted = true
    this.videoEl.srcObject = this.stream
    document.body.appendChild(this.videoEl)
    await this.videoEl.play()

    this.faceMesh = new FaceMesh({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
    })
    this.faceMesh.setOptions({
      maxNumFaces: 3,
      refineLandmarks: false,
      minDetectionConfidence: 0.5,
    })
    this.faceMesh.onResults((results) => {
      this.lastResultCount = results.multiFaceLandmarks?.length ?? 0
    })

    this.statusListener?.('active', 'Camera monitoring is active for this interview')

    // 2fps polling for CPU-friendly proctoring checks.
    this.intervalId = window.setInterval(async () => {
      if (!this.faceMesh || !this.videoEl || this.busy) return
      this.busy = true
      try {
        await this.faceMesh.send({ image: this.videoEl })
        const faces = this.lastResultCount
        const now = Date.now()
        if (faces === 0) {
          if (this.absentStartedAt === null) this.absentStartedAt = now
          const absentSeconds = Math.floor((now - this.absentStartedAt) / 1000)
          if (absentSeconds >= 15) {
            this.emit('face_absent', 'high', { absent_seconds: absentSeconds })
            this.absentStartedAt = null
          }
        } else {
          this.absentStartedAt = null
          if (faces >= 2) {
            this.emit('multi_face', 'high', { face_count: faces })
          }
        }
      } catch {
        this.statusListener?.('error', 'Camera monitoring error')
      } finally {
        this.busy = false
      }
    }, 500)
  }

  handlePermissionDenied() {
    this.statusListener?.('denied', 'Camera access recommended for this interview')
  }

  stop() {
    if (this.intervalId) window.clearInterval(this.intervalId)
    this.intervalId = null
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop())
    }
    this.stream = null
    if (this.videoEl && this.videoEl.parentNode) this.videoEl.parentNode.removeChild(this.videoEl)
    this.videoEl = null
    this.faceMesh = null
    this.absentStartedAt = null
    this.lastResultCount = 0
    this.busy = false
  }
}

