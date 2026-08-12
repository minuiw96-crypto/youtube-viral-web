-- Run once in Supabase Dashboard > SQL Editor.
create extension if not exists vector with schema extensions;

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 100),
  role text not null default 'user' check (role in ('user', 'admin')),
  channel_input text,
  channel_id text,
  channel_title text,
  channel_status text not null default 'not_found',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_profiles enable row level security;

drop policy if exists "users_read_own_profile" on public.user_profiles;
create policy "users_read_own_profile"
on public.user_profiles for select
to authenticated
using ((select auth.uid()) = id);

create table if not exists public.rag_documents (
  id text primary key,
  channel_id text not null default 'GLOBAL',
  title text not null,
  aliases text[] not null default '{}',
  topic text,
  content text not null,
  doc_type text not null default 'feature_metric_definition',
  knowledge_version text,
  schema_version text,
  embedding_model text,
  embedding_dimensions integer,
  "contentVector" jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists rag_documents_channel_id_idx
on public.rag_documents(channel_id);

alter table public.rag_documents enable row level security;
-- No client policies: only the backend Secret Key can read or modify RAG documents.
