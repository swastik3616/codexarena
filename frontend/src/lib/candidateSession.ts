type InterviewQuestion = {
  question_id: string
  title: string
  description: string
  difficulty?: 'easy' | 'medium' | 'hard'
  topic_tags?: string[]
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

let session: CandidateSession | null = null

export const setCandidateSession = (next: CandidateSession) => {
  session = next
}

export const getCandidateSession = (): CandidateSession | null => session

export const clearCandidateSession = () => {
  session = null
}

export type { CandidateSession, InterviewQuestion }

