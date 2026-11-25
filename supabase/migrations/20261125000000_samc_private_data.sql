-- declaration_list · 고객사 자료(SAMC_DATA) 표와 원본 Storage (2026-11-25, PM 결정)
-- 이 파일은 2026-11-25 Supabase에 적용한 samc_private_data 마이그레이션을 저장소에 남긴 것이다.
-- 여러 번 실행해도 같은 결과가 나오게 썼다(if not exists, drop policy if exists).
-- 원칙: 화주 실명은 넣지 않는다(shipper는 A기업·B기업 가명). 드라이브·시트 ID도 넣지 않는다.
-- 권한: 로그인한 프로그램 계정(authenticated)만 읽는다. anon은 읽지 못한다.
--       쓰기 정책이 없으므로 service_role(secret 키, PM만 보관)으로만 쓸 수 있다.

create table if not exists public.samc_files (
  path          text primary key,        -- SAMC_DATA 안 상대 경로
  top           text not null,           -- 최상위 폴더
  category      text not null,           -- intake · shipping_docs · inspection_data · sheet · law · company_program
  doc_kind      text,                    -- 서류 종류 (CI·PL·BL·수입신고서·시험성적서 …)
  shipper       text,                    -- A기업 · B기업 (가명)
  ext           text,                    -- 확장자
  size          bigint,                  -- 바이트
  sha256        text not null,           -- 원본 해시
  storage_path  text                     -- samc-originals 버킷 안 이름: <sha256><확장자>
);

create table if not exists public.samc_texts (
  path   text not null references public.samc_files(path) on delete cascade,
  part   text not null,                  -- p1 · 시트명 · ocr_p1 …
  text   text not null,
  primary key (path, part)
);

create table if not exists public.samc_json (
  path      text primary key,
  category  text,
  shipper   text,
  body      jsonb not null
);

create table if not exists public.samc_sheet_rows (
  workbook  text not null,               -- 엑셀 파일 경로
  sheet     text not null,
  row_no    integer not null,
  cells     jsonb not null,
  primary key (workbook, sheet, row_no)
);

alter table public.samc_files      enable row level security;
alter table public.samc_texts      enable row level security;
alter table public.samc_json       enable row level security;
alter table public.samc_sheet_rows enable row level security;

drop policy if exists "read samc_files"      on public.samc_files;
drop policy if exists "read samc_texts"      on public.samc_texts;
drop policy if exists "read samc_json"       on public.samc_json;
drop policy if exists "read samc_sheet_rows" on public.samc_sheet_rows;
create policy "read samc_files"      on public.samc_files      for select to authenticated using (true);
create policy "read samc_texts"      on public.samc_texts      for select to authenticated using (true);
create policy "read samc_json"       on public.samc_json       for select to authenticated using (true);
create policy "read samc_sheet_rows" on public.samc_sheet_rows for select to authenticated using (true);

-- 원본 파일: 비공개 버킷. 로그인한 계정만 읽는다.
insert into storage.buckets (id, name, public)
values ('samc-originals', 'samc-originals', false)
on conflict (id) do update set public = false;

drop policy if exists "read samc-originals" on storage.objects;
create policy "read samc-originals" on storage.objects
  for select to authenticated using (bucket_id = 'samc-originals');
