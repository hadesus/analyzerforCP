/*
  # Create protocols storage tables

  1. New Tables
    - `protocols`
      - `id` (uuid, primary key)
      - `filename` (text)
      - `upload_date` (timestamp)
      - `document_summary` (text)
      - `analysis_results` (jsonb)
      - `user_id` (uuid, foreign key to auth.users)
      - `created_at` (timestamp)
      - `updated_at` (timestamp)
    - `protocol_drugs`
      - `id` (uuid, primary key)
      - `protocol_id` (uuid, foreign key)
      - `drug_name_source` (text)
      - `inn_name` (text)
      - `dosage_source` (text)
      - `grade_level` (text)
      - `summary_note` (text)
      - `created_at` (timestamp)

  2. Security
    - Enable RLS on both tables
    - Add policies for authenticated users to manage their own protocols
    - Add policies for reading and writing protocol data

  3. Indexes
    - Add indexes for efficient querying by user_id and upload_date
*/

-- Create protocols table
CREATE TABLE IF NOT EXISTS protocols (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  upload_date timestamptz DEFAULT now(),
  document_summary text,
  analysis_results jsonb DEFAULT '[]'::jsonb,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create protocol_drugs table for easier querying
CREATE TABLE IF NOT EXISTS protocol_drugs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  protocol_id uuid REFERENCES protocols(id) ON DELETE CASCADE,
  drug_name_source text NOT NULL,
  inn_name text,
  dosage_source text,
  grade_level text,
  summary_note text,
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE protocol_drugs ENABLE ROW LEVEL SECURITY;

-- Policies for protocols table
CREATE POLICY "Users can read own protocols"
  ON protocols
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own protocols"
  ON protocols
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own protocols"
  ON protocols
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own protocols"
  ON protocols
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Policies for protocol_drugs table
CREATE POLICY "Users can read own protocol drugs"
  ON protocol_drugs
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM protocols 
      WHERE protocols.id = protocol_drugs.protocol_id 
      AND protocols.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own protocol drugs"
  ON protocol_drugs
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM protocols 
      WHERE protocols.id = protocol_drugs.protocol_id 
      AND protocols.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update own protocol drugs"
  ON protocol_drugs
  FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM protocols 
      WHERE protocols.id = protocol_drugs.protocol_id 
      AND protocols.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM protocols 
      WHERE protocols.id = protocol_drugs.protocol_id 
      AND protocols.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own protocol drugs"
  ON protocol_drugs
  FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM protocols 
      WHERE protocols.id = protocol_drugs.protocol_id 
      AND protocols.user_id = auth.uid()
    )
  );

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_protocols_user_id ON protocols(user_id);
CREATE INDEX IF NOT EXISTS idx_protocols_upload_date ON protocols(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_protocol_drugs_protocol_id ON protocol_drugs(protocol_id);
CREATE INDEX IF NOT EXISTS idx_protocol_drugs_inn_name ON protocol_drugs(inn_name);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_protocols_updated_at 
  BEFORE UPDATE ON protocols 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();