-- declaration_list · Supabase 공개 정보 테이블 (2026-11-24, 초안)
-- 원칙: 공개 정보만 둔다. 화주명·화주 서류·실적·신고 이력은 절대 넣지 않는다.
-- 권한: 팀원(anon/authenticated)은 읽기만. 쓰기는 service_role(PM만 보관)으로만 한다.

create table if not exists public.material_codes (
  name        text primary key,          -- 재질 코드명 (예: 금속제(불소수지도장))
  code        text,                      -- 14자리 재질 코드 (예: D5000002B20000), 모르면 null
  source      text not null,             -- 출처 (식약처 성분코드 API / 법령자료 03)
  as_of       date not null              -- 기준일
);

create table if not exists public.material_aliases (
  alias       text primary key,          -- 표기 (약어·다른 표기, 예: PP, 스테인리스)
  name        text not null,             -- 공식 재질 코드명
  source      text not null,
  as_of       date not null
);

create table if not exists public.law_documents (
  doc_no      text primary key,          -- 문서 번호 (예: 01)
  title       text not null,             -- 예: 공전 원문 (현행)
  body        text not null,             -- 본문 텍스트
  source      text not null,             -- 원 출처 (법제처·식품안전나라·수입식품정보마루)
  as_of       date not null,             -- 기준일 (최신본 확인 필요)
  char_count  integer generated always as (char_length(body)) stored
);

create table if not exists public.fx_rates (
  week_start  date not null,             -- 관세환율 적용 주 시작일
  currency    text not null,             -- 통화 코드 (USD, CNY, JPY …)
  rate_krw    numeric(18,6) not null,    -- 1단위당 원화
  source      text not null default 'UNIPASS 관세환율',
  primary key (week_start, currency)
);

alter table public.material_codes   enable row level security;
alter table public.material_aliases enable row level security;
alter table public.law_documents    enable row level security;
alter table public.fx_rates         enable row level security;

-- 읽기만 허용 (쓰기 정책이 없으므로 service_role 외에는 쓸 수 없다)
create policy "read material_codes"   on public.material_codes   for select to anon, authenticated using (true);
create policy "read material_aliases" on public.material_aliases for select to anon, authenticated using (true);
create policy "read law_documents"    on public.law_documents    for select to anon, authenticated using (true);
create policy "read fx_rates"         on public.fx_rates         for select to anon, authenticated using (true);
