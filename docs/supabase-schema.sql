-- trend_items 테이블 생성
CREATE TABLE trend_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,

  metadata JSONB DEFAULT '{}',

  relevance_score INT,
  summary TEXT,
  matched_interests TEXT[],
  code_example TEXT,

  license TEXT,
  is_open_source BOOLEAN DEFAULT false,

  first_seen_at TIMESTAMPTZ DEFAULT now(),
  last_seen_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(source, source_id)
);

-- 인덱스 생성
-- 참고: UNIQUE(source, source_id) 제약조건이 자동으로 유니크 인덱스를 생성함
CREATE INDEX idx_trend_items_source ON trend_items(source);
CREATE INDEX idx_trend_items_first_seen ON trend_items(first_seen_at DESC);
CREATE INDEX idx_trend_items_relevance ON trend_items(relevance_score DESC);

-- RLS (Row Level Security) 활성화
ALTER TABLE trend_items ENABLE ROW LEVEL SECURITY;

-- 공개 읽기 정책 (대시보드용)
CREATE POLICY "Public read access" ON trend_items
  FOR SELECT USING (true);

-- Service role만 쓰기 가능
CREATE POLICY "Service role write access" ON trend_items
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
