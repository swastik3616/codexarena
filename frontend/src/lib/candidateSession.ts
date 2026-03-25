type InterviewQuestion = {
  question_id: string
  title: string
  description: string
  difficulty?: 'easy' | 'medium' | 'hard'
  topic_tags?: string[]
  constraints?: string[]
  examples?: Array<{ input: string; output: string; explanation?: string }>
  hints?: string[]
}

type CandidateSession = {
  roomId: string
  candidateId: string
  candidateToken: string
  attemptId?: string
  question?: InterviewQuestion
}

const SESSION_KEY = 'candidateSession'
let session: CandidateSession | null = null

export const setCandidateSession = (next: CandidateSession) => {
  session = next
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(next))
  } catch {
    // ignore storage errors
  }
}

export const getCandidateSession = (): CandidateSession | null => {
  if (session) return session
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (raw) {
      session = JSON.parse(raw) as CandidateSession
      return session
    }
  } catch {
    // ignore parse errors
  }
  return null
}

export const clearCandidateSession = () => {
  session = null
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore storage errors
  }
}

export type { CandidateSession, InterviewQuestion }

