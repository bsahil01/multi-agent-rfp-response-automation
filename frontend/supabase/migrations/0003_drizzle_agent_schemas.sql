-- Drizzle ORM agent schemas migration
-- This migration adds the agent interaction tables using Drizzle schema definitions

-- Message type enum
DO $$ BEGIN
    CREATE TYPE "public"."message_type" AS ENUM('user', 'assistant');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Interaction type enum
DO $$ BEGIN
    CREATE TYPE "public"."interaction_type" AS ENUM('response', 'tool_call', 'error');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Chat sessions table for persisting agent state
CREATE TABLE IF NOT EXISTS "chat_sessions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "session_id" text UNIQUE NOT NULL,
  "current_step" text DEFAULT 'IDLE',
  "next_node" text DEFAULT 'main_agent',
  "rfps_identified" jsonb DEFAULT '[]',
  "selected_rfp" jsonb,
  "user_selected_rfp_id" text,
  "technical_analysis" jsonb,
  "pricing_analysis" jsonb,
  "final_response" text,
  "report_path" text,
  "product_summary" text,
  "test_summary" text,
  "waiting_for_user" boolean DEFAULT false,
  "user_prompt" text,
  "error" text,
  "created_at" timestamp DEFAULT now(),
  "updated_at" timestamp DEFAULT now()
);

-- Chat messages table for conversation history
CREATE TABLE IF NOT EXISTS "chat_messages" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "session_id" text NOT NULL,
  "message_type" "message_type" NOT NULL,
  "content" text NOT NULL,
  "metadata" jsonb DEFAULT '{}',
  "created_at" timestamp DEFAULT now()
);

-- Agent interactions table for detailed agent tracking
CREATE TABLE IF NOT EXISTS "agent_interactions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "session_id" text NOT NULL,
  "agent_name" text NOT NULL,
  "interaction_type" "interaction_type" DEFAULT 'response',
  "input_data" jsonb DEFAULT '{}',
  "output_data" jsonb DEFAULT '{}',
  "reasoning" text,
  "tool_calls" jsonb DEFAULT '[]',
  "created_at" timestamp DEFAULT now()
);

-- Enhanced RFPs table with analysis fields (add columns if they don't exist)
DO $$
BEGIN
    -- Add analysis columns to rfps_table if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'status') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "status" text DEFAULT 'identified';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'priority_score') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "priority_score" integer DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'budget_range') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "budget_range" text;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'technical_requirements') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "technical_requirements" jsonb DEFAULT '[]';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'sales_analysis') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "sales_analysis" jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'technical_analysis') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "technical_analysis" jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'pricing_analysis') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "pricing_analysis" jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'rfps_table' AND column_name = 'updated_at') THEN
        ALTER TABLE "rfps_table" ADD COLUMN "updated_at" timestamp DEFAULT now();
    END IF;
END $$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS "chat_sessions_session_id_idx" ON "chat_sessions"("session_id");
CREATE INDEX IF NOT EXISTS "chat_messages_session_id_idx" ON "chat_messages"("session_id");
CREATE INDEX IF NOT EXISTS "chat_messages_created_at_idx" ON "chat_messages"("created_at");
CREATE INDEX IF NOT EXISTS "agent_interactions_session_id_idx" ON "agent_interactions"("session_id");
CREATE INDEX IF NOT EXISTS "agent_interactions_agent_name_idx" ON "agent_interactions"("agent_name");
CREATE INDEX IF NOT EXISTS "rfps_table_status_idx" ON "rfps_table"("status");

-- RLS (Row Level Security) policies for new tables
ALTER TABLE "chat_sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "chat_messages" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "agent_interactions" ENABLE ROW LEVEL SECURITY;

-- Users can access their own sessions
CREATE POLICY IF NOT EXISTS "Users can view own chat sessions" ON "chat_sessions"
  FOR SELECT USING (auth.uid()::text = session_id);

CREATE POLICY IF NOT EXISTS "Users can insert own chat sessions" ON "chat_sessions"
  FOR INSERT WITH CHECK (auth.uid()::text = session_id);

CREATE POLICY IF NOT EXISTS "Users can update own chat sessions" ON "chat_sessions"
  FOR UPDATE USING (auth.uid()::text = session_id);

-- Users can access their own messages
CREATE POLICY IF NOT EXISTS "Users can view own chat messages" ON "chat_messages"
  FOR SELECT USING (auth.uid()::text = session_id);

CREATE POLICY IF NOT EXISTS "Users can insert own chat messages" ON "chat_messages"
  FOR INSERT WITH CHECK (auth.uid()::text = session_id);

-- Users can access their own agent interactions
CREATE POLICY IF NOT EXISTS "Users can view own agent interactions" ON "agent_interactions"
  FOR SELECT USING (auth.uid()::text = session_id);

CREATE POLICY IF NOT EXISTS "Users can insert own agent interactions" ON "agent_interactions"
  FOR INSERT WITH CHECK (auth.uid()::text = session_id);
