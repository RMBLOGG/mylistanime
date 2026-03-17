-- Jalankan query ini di Supabase SQL Editor
-- Dashboard → SQL Editor → New Query → paste ini → Run

CREATE TABLE anime_lists (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  username TEXT NOT NULL,
  anime_list JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE anime_lists ENABLE ROW LEVEL SECURITY;

-- Policy: siapapun bisa baca (public)
CREATE POLICY "Anyone can read lists"
  ON anime_lists FOR SELECT
  USING (true);

-- Policy: siapapun bisa insert (no auth required)
CREATE POLICY "Anyone can insert lists"
  ON anime_lists FOR INSERT
  WITH CHECK (true);
