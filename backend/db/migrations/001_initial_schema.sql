-- CodexArena initial schema
-- Requires: pgcrypto for gen_random_uuid()

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE recruiters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  company VARCHAR(100),
  plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free','pro','enterprise')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE rooms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recruiter_id UUID NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','active','completed','archived')),
  join_token VARCHAR(64) UNIQUE NOT NULL,
  question_id UUID,
  difficulty VARCHAR(10) DEFAULT 'medium' CHECK (difficulty IN ('easy','medium','hard')),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255),
  status VARCHAR(20) DEFAULT 'waiting' CHECK (status IN ('waiting','coding','submitted','evaluated')),
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  submitted_at TIMESTAMPTZ
);

CREATE TABLE questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  difficulty VARCHAR(10) NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
  topic_tags TEXT[] DEFAULT '{}',
  test_cases JSONB NOT NULL DEFAULT '[]',
  validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending','validated','failed')),
  generated_by VARCHAR(10) DEFAULT 'ai' CHECK (generated_by IN ('ai','manual')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  question_id UUID NOT NULL REFERENCES questions(id),
  language VARCHAR(20) NOT NULL DEFAULT 'python' CHECK (language IN ('python','javascript','java','cpp','go')),
  final_code TEXT,
  s3_archive_key VARCHAR(300),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  submitted_at TIMESTAMPTZ
);

CREATE TABLE execution_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  test_pass_count INTEGER DEFAULT 0,
  test_total INTEGER DEFAULT 0,
  stdout TEXT,
  stderr TEXT,
  exit_code INTEGER,
  wall_time_ms INTEGER,
  memory_kb INTEGER,
  timed_out BOOLEAN DEFAULT FALSE,
  executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  correctness_score SMALLINT DEFAULT 0 CHECK (correctness_score BETWEEN 0 AND 40),
  efficiency_score SMALLINT DEFAULT 0 CHECK (efficiency_score BETWEEN 0 AND 30),
  readability_score SMALLINT DEFAULT 0 CHECK (readability_score BETWEEN 0 AND 20),
  edge_case_score SMALLINT DEFAULT 0 CHECK (edge_case_score BETWEEN 0 AND 10),
  total_score SMALLINT GENERATED ALWAYS AS (correctness_score + efficiency_score + readability_score + edge_case_score) STORED,
  big_o_time VARCHAR(20),
  big_o_space VARCHAR(20),
  feedback TEXT,
  suggestions JSONB DEFAULT '[]',
  prompt_version VARCHAR(20) DEFAULT 'v1',
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cheat_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  event_type VARCHAR(30) NOT NULL CHECK (
    event_type IN (
      'tab_switch',
      'large_paste',
      'face_absent',
      'multi_face',
      'idle_timeout',
      'copy_detected',
      'keystroke_anomaly',
      'solution_similarity'
    )
  ),
  severity VARCHAR(10) NOT NULL CHECK (severity IN ('low','medium','high')),
  payload JSONB DEFAULT '{}',
  occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rooms_recruiter ON rooms(recruiter_id);
CREATE INDEX idx_candidates_room ON candidates(room_id);
CREATE INDEX idx_attempts_candidate ON attempts(candidate_id);
CREATE INDEX idx_execution_attempt ON execution_results(attempt_id);
CREATE INDEX idx_ai_eval_attempt ON ai_evaluations(attempt_id);
CREATE INDEX idx_cheat_candidate ON cheat_events(candidate_id);
CREATE INDEX idx_cheat_occurred ON cheat_events(occurred_at DESC);

COMMIT;

