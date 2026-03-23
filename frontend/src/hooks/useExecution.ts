import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'
import type { EditorLanguage } from '../store/editorStore'

type ExecuteResultItem = {
  test_id: number | string
  passed: boolean
  actual: string
  time_ms: number
}

export type ExecuteResult = {
  status: 'complete'
  pass_count: number
  total: number
  stdout?: string
  stderr?: string
  wall_time_ms?: number
  timed_out: boolean
  results: ExecuteResultItem[]
}

type UseExecutionParams = {
  apiBaseUrl?: string
  candidateToken?: string
}

type RunParams = {
  attemptId: string
  language: EditorLanguage
  code: string
}

export const useExecution = ({ apiBaseUrl = 'http://127.0.0.1:8000', candidateToken }: UseExecutionParams) => {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ExecuteResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [cooldownSeconds, setCooldownSeconds] = useState(0)
  const cooldownTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (cooldownSeconds <= 0) return
    const id = window.setTimeout(() => setCooldownSeconds((n) => Math.max(0, n - 1)), 1000)
    cooldownTimerRef.current = id
    return () => window.clearTimeout(id)
  }, [cooldownSeconds])

  const run = useCallback(
    async ({ attemptId, language, code }: RunParams) => {
      if (cooldownSeconds > 0 || loading) return

      setLoading(true)
      setError(null)
      setResult(null)
      setJobId(null)

      try {
        const post = await axios.post(
          `${apiBaseUrl}/execute`,
          {
            attempt_id: attemptId,
            language,
            code,
          },
          {
            headers: candidateToken ? { Authorization: `Bearer ${candidateToken}` } : undefined,
          },
        )

        const newJobId = post.data?.job_id as string
        setJobId(newJobId)

        // Poll for completion every 1s
        while (true) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          const get = await axios.get(`${apiBaseUrl}/execute/${newJobId}`, {
            headers: candidateToken ? { Authorization: `Bearer ${candidateToken}` } : undefined,
          })

          if (get.data?.status === 'complete') {
            setResult(get.data as ExecuteResult)
            break
          }
        }
      } catch (e: unknown) {
        if (axios.isAxiosError(e) && e.response?.status === 429) {
          const retryAfterHeader = e.response.headers?.['retry-after']
          const retryAfter = Number(retryAfterHeader ?? 5)
          setCooldownSeconds(Number.isFinite(retryAfter) ? retryAfter : 5)
          setError(`Rate limited. Run again in ${Number.isFinite(retryAfter) ? retryAfter : 5}s`)
        } else if (axios.isAxiosError(e)) {
          setError(e.response?.data?.detail ?? e.message)
        } else {
          setError('Execution failed')
        }
      } finally {
        setLoading(false)
      }
    },
    [apiBaseUrl, candidateToken, cooldownSeconds, loading],
  )

  return {
    run,
    loading,
    result,
    error,
    jobId,
    cooldownSeconds,
  }
}

