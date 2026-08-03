-- =============================================================
--  Patient List — Supabase 資料表
--  用法：Supabase 專案 → 左側 SQL Editor → New query → 全部貼上 → Run
--  可重複執行，不會刪除既有資料。
--
--  設計重點：**伺服器端看不到任何病人資料**。
--  病人內容在瀏覽器裡用 AES-GCM 加密後才上傳，這裡只存密文（payload）。
--  因此沒有 mrn / name / 日期 等欄位，也無法在資料庫端搜尋或排序——
--  查詢、篩選、排序一律在使用者的瀏覽器內完成。
-- =============================================================

create extension if not exists pgcrypto;

-- ---------- 金鑰資料（每個使用者一列）----------
-- salt      : PBKDF2 的鹽（隨機 16 bytes，base64）
-- verifier  : 用資料密碼加密一段已知字串，登入時用來確認密碼打對了
-- 這兩個值外洩也解不開資料（沒有資料密碼），但仍受 RLS 保護。
create table if not exists public.vault (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  salt        text not null,
  verifier    text not null,
  iters       int  not null default 250000,
  created_at  timestamptz not null default now()
);

-- ---------- 病人（一人一列，內容全部加密在 payload）----------
create table if not exists public.patients (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  payload     text not null,                       -- base64(iv ‖ ciphertext)
  rev         int  not null default 1,             -- 每次存檔 +1，用來偵測跨裝置覆蓋
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists patients_user on public.patients (user_id, updated_at desc);

-- updated_at 自動更新
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists patients_touch on public.patients;
create trigger patients_touch before update on public.patients
  for each row execute function public.touch_updated_at();

-- =============================================================
--  Row Level Security：每個人只讀得到自己的資料
-- =============================================================
alter table public.vault    enable row level security;
alter table public.patients enable row level security;

do $$
declare t text;
begin
  foreach t in array array['vault','patients'] loop
    execute format('drop policy if exists own_select on public.%I', t);
    execute format('drop policy if exists own_insert on public.%I', t);
    execute format('drop policy if exists own_update on public.%I', t);
    execute format('drop policy if exists own_delete on public.%I', t);

    execute format('create policy own_select on public.%I for select using (auth.uid() = user_id)', t);
    execute format('create policy own_insert on public.%I for insert with check (auth.uid() = user_id)', t);
    execute format('create policy own_update on public.%I for update using (auth.uid() = user_id) with check (auth.uid() = user_id)', t);
    execute format('create policy own_delete on public.%I for delete using (auth.uid() = user_id)', t);
  end loop;
end $$;
