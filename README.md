# 기구·용기·포장 검역 신고 리스트 자동 작성 및 이력 관리 프로그램

> 상태: 초안 · 작성일: 2026-11-24 · 작성: KHS(PM)
> 기준 자료: ① 기업 제안서 ② SAMC 발표자료 PDF ③ 11/24 SAMC 미팅 정리 ④ Leafn 저장소 구조 ⑤ SAMC 기존 도구 공유본
> KITA 무역 AX마스터 2기 최종 프로젝트 2조 · 기업 과제(SAMC 관세사무소) 1~4번

**한 줄 요약:** 화주가 보낸 선적서류를 올리면 검역이력 행이 만들어지고, 재질·실적이 근거와 함께 골라지고, 신고건으로 묶여 유니패스에 올릴 품목사항 엑셀까지 나오는 프로그램입니다. 실제 신고는 하지 않으며 최종 판단은 담당자가 합니다.

---

## 해결하려는 문제

| 지금 담당자가 하는 일 | 문제 | 이 프로그램 |
|---|---|---|
| 인보이스·패킹리스트·B/L을 보며 시트에 한 칸씩 입력 | 반복 입력, 오타 | 서류 판독 → 검역이력 행 자동 생성, 서류끼리 대조 |
| 제품마다 과거 이력·실적을 찾아 재질·실적번호 대조 | 시간이 많이 들고 놓치기 쉬움 | 재질 판단 순서·재질 포함 규칙으로 후보와 근거 제시 |
| 화주마다 다른 묶음·서류 규칙을 머릿속으로 적용 | 담당자가 바뀌면 끊김 | 화주 설정 화면에 규칙을 스위치로 기록 |
| 실적 만료일을 따로 관리 | 만료 실적 사용 위험 | 실적 탭(만료 취소선) + 3개월·1개월 전 알림 메일 |

---

## 문서

| 문서 | 누가 읽나 | 내용 |
|---|---|---|
| [AGENTS.md](AGENTS.md) | AI 코딩 도구, 개발자 | 기술 판단 기준, 기능 목록, 구조, 데이터, API, 작업 프롬프트 |
| [RULES.md](RULES.md) | 팀 전원 | Git·PR·코드·보안 규칙, **업무 규칙**(신고건·재질·실적·화주별) |
| [DESIGN.md](DESIGN.md) | 화면 담당 | 화면 설계, 화면별 상태·버튼·API |
| [CLAUDE.md](CLAUDE.md) | Claude Code | AGENTS.md를 가리킴 |

문서가 서로 다르면 AGENTS > RULES > DESIGN > README 순서로 따릅니다.

---

## 업무와 담당

| 번호 | 담당 | 기능 | 화면 | 폴더 |
|---|---|---|---|---|
| 1 | KHS (PM) | 서류 판독, 검역이력 행 생성, 서류 대조, 검수 패널, 메인 화면, 공통 코드·DB, (후순위) 유니패스 반입 상태 | 탭 1. 검역 리스트 (`/`) | `backend/app/core/` `a0_reader/` `a1_history/` `law_data/`, `frontend/app/page.tsx` `components/home/` `components/reader/` `review/` |
| 2 | YHS | 수입신고서·성적서 등록, 실적 표, 해외제조업소 코드 갱신, 만료 알림 메일(3·1개월 전) | 탭 2. 서류 등록·만료 알림 (`/registry`) | `backend/app/a2_registry/`, `frontend/app/registry/` `components/registry/` |
| 3 | LSY | 재질·실적·제조사 판단, 신고건 묶음, 품목사항 엑셀 | 탭 3. 재질·실적 판단 (`/judge`) | `backend/app/a3_judge/`, `frontend/app/judge/` `components/judge/` |
| 4 | JUJ | 화주 설정(공통 규칙 / 화주별 선택 규칙), 규칙 적용 엔진 | 탭 4. 기업 설정 (`/settings`) | `backend/app/a4_settings/` `rules/`, `frontend/app/settings/` `components/settings/` |

탭 4개 = 제안서 가이드라인 1~4번 = 담당 1명씩(1인 1탭). 5·6번(주간 보고서)은 weekly_report 저장소에서 한다.

자세한 기능 ID·우선순위는 [AGENTS.md 1장](AGENTS.md#1장-기능-목록과-상태).

---

## 시연 시나리오

제안서 최종 산출물 ①의 **대표 시나리오 3종**이다. 모두 가상 화주 **A사(가전)**, **B사(주방용품)** 와 `samples/`의 가상 서류로 한다. 세부 시나리오는 착수 후 멘토와 확정한다 [제안서].

| | 시나리오 | 흐름 | 쓰는 기능 | 담당 |
|---|---|---|---|---|
| (a) | **신규 B/L → 행 자동 생성·실적 선택·품목사항 엑셀** | A사 B/L 폴더 올리기 → 판독 → 검역이력 행 생성(빠진 서류는 "자료 추가 필요") → 이력·등록 데이터로 재질·제조사 코드 → 유효 실적 자동 선택(근거 표시) → 신고건 묶음 → 품목사항 엑셀 다운로드 | A0·A1·A3 | KHS·LSY |
| (b) | **수입신고서·검사성적서 등록 → 만료 알림** | 수입신고서·검사성적서 올리기 → 제품별 재질·해외제조업소·실적 등록 → 실적 탭에서 만료일·취소선 확인 → 3개월·1개월 전 알림 메일 → (a)의 새 행에서 그 데이터로 재질·실적이 채워지는 것 확인 | A2·A3 | YHS·LSY |
| (c) | **서류 불일치 검수** | 금액·포장 수가 서로 다른 가상 서류 올리기 → 불일치 칸 빨강 → 행 선택 → 아래 검수 패널에서 서류별 값 비교 → 담당자가 값 고침(주황 + 메모) → 확인함 → 배지 숫자 감소 | A1-3·A1-4 | KHS |
| 추가 | **설정만으로 다른 결과** (제안서 4번) | 같은 형태의 서류를 A사·B사로 처리 → A사는 부분품을 한 행으로 합치고 모선·제조사·재질로 묶음, B사는 색상(내색)으로 나누고 5행씩 끊음 → 화주 설정에서 스위치 하나를 바꿔 [시험 실행]으로 전/후 비교 | A4·A3 | JUJ·LSY |

**성과지표 (후보, 확인 필요)** [제안서 확인요청사항 ③]
| 지표 | 재는 법 |
|---|---|
| 판독 정확도 | SAMC가 준 정답 검역이력 행과 칸별 일치율(B/L 10~20건) |
| 실적 선택 일치율 | 담당자가 실제로 쓴 실적번호와 일치하는 비율 |
| 처리 시간 | 서류 올리기 → 품목사항 엑셀까지 걸린 시간(수기 대비) |

---

## 폴더 구조

**1 기능 = 1 폴더 = 1 담당자**로 나눠서 같은 파일을 동시에 고치는 일을 막습니다. 각자 자기 폴더 안에서만 작업합니다.

```
declaration_list/
├─ backend/app/
│  ├─ main.py                       KHS (영역 라우터 6개만, 고정)
│  ├─ core/                         KHS  schema/ llm.py masking.py unipass/ fx.py storage/
│  ├─ law_data/                     KHS  material_codes/ law_docs/ fx_rates/
│  ├─ a0_reader/      (1번 KHS)     classify/ extract/ upload/
│  ├─ a1_history/     (1번 KHS)     rows/ missing/ crosscheck/ review/ archive/ arrival/ price/
│  ├─ a2_registry/    (2번 YHS)     upload/ products/ records/ alerts/ factory_codes/ drive_sync/
│  ├─ a3_judge/       (3번 LSY)     pipeline/ history_lookup/ material/ spec_class/ factory/ record_pick/
│  │                                color/ spare_parts/ rule_check/ grouping/ item_sheet/ ai_material/  (AGENTS 4-5)
│  └─ a4_settings/    (4번 JUJ)     shippers/ catalog/ engine/ dry_run/
│     └─ (기능 폴더마다) router.py service.py models.py tests/
├─ backend/prompts/<영역>/  rules/ (JUJ)  templates/ (LSY)  scripts/seed/ (KHS)  tests/e2e/ (KHS)
├─ frontend/
│  ├─ app/            layout.tsx·page.tsx (KHS, 탭 1)  registry/ (YHS, 탭 2)  judge/ (LSY, 탭 3)  settings/ (JUJ, 탭 4)
│  ├─ components/     ui/ (공통)  home/·reader/·review/ (KHS)  registry/ (YHS)  judge/ (LSY)  settings/ (JUJ)
│  └─ lib/            api/<영역>.ts  text/<영역>.ts  types/ (KHS)
├─ supabase/migrations/ (KHS)   samples/A/ samples/B/   data/ (git 제외)
└─ docs/              handover/ meetings/ (KHS)   notes/<이니셜>/ (각자)
```

기능 폴더별 설명, 충돌이 잘 나는 파일과 대처는 [AGENTS.md 4장](AGENTS.md#4장-저장소-구조)에 있습니다.

---

## 실행 방법

준비: Python 3.12, Node.js 20 이상, Git.

**1. 환경 변수**
```bash
cp .env.example .env            # Windows: copy .env.example .env
```
**팀원 `.env`에 넣을 것** (나머지는 비워 둬도 실행됩니다)
| 변수 | 값 | 어디서 |
|---|---|---|
| `SUPABASE_URL` | `https://cqxmndycpbozjfrtlvbi.supabase.co` | `.env.example`에 이미 들어 있음 |
| `SUPABASE_ANON_KEY` | `sb_publishable_…` | PM에게 받기 (대시보드 Project Settings → API Keys → publishable 키) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | 프로그램 계정 1개 | PM에게 직접 받기 (채팅·커밋 금지) |
| `AUTH_SECRET_KEY` | 아무 긴 무작위 문자열 | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY` | 각자 AI 키 | 각 사이트에서 발급 (없으면 `LLM_ENABLED=false`) |

`SUPABASE_SERVICE_ROLE_KEY`(secret 키)는 **PM만** 넣습니다. 팀원은 비워 둡니다. 키가 없어도 `LLM_ENABLED=false`, `UNIPASS_MODE=mock`으로 실행할 수 있습니다.

**PM만: 자료 적재**
```bash
python backend/scripts/seed/build_local_seed.py "C:/Users/user/Desktop/SAMC_DATA" data/app.db
python backend/scripts/seed/push_supabase.py      # .env에 secret 키를 넣은 뒤
```
Supabase 대시보드: https://supabase.com/dashboard/project/cqxmndycpbozjfrtlvbi

화면 쪽은 `frontend/.env.local`에 한 줄을 넣습니다.
```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api
```

**2. 백엔드**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
확인: http://127.0.0.1:8000/api/core/health

**3. 화면**
```bash
cd frontend
npm install
npm run dev
```
확인: http://localhost:3000 → **로그인 화면**이 먼저 나옵니다. `.env`의 `ADMIN_USERNAME`·`ADMIN_PASSWORD`(프로그램 계정 1개)로 로그인합니다.

**4. 점검 (PR 전)**
```bash
cd backend && pytest && ruff check .
cd frontend && npm run typecheck && npm run lint && npm run build
```

---

## 브랜치

```
main  ←  dev  ←  KHS / YHS / LSY / JUJ
```
- 각자 본인 브랜치에서 작업하고 `dev`로 PR합니다. 모든 PR은 PM(KHS)이 확인하고 수락합니다(테스트 통과 필수).
- `main`은 PM이 `dev`에서 합칩니다. `main`·`dev`에 직접 push하지 않습니다.
- 자세한 규칙: [RULES.md 1~3장](RULES.md#1-브랜치).

---

## 이관 산출물

제안서 "기업 이관 관련" 항목에 맞춘다.

| 산출물 | 위치 | 상태 |
|---|---|---|
| 소스코드·Git 링크 | 이 저장소 `main` | 진행 중 |
| 외부 API·DB 이름과 설정값 목록(값 없이) | [.env.example](.env.example), [AGENTS.md 8·9장](AGENTS.md#8장-외부-연동) | 초안 |
| 표준 로직(공통 규칙) 목록 | [RULES.md 11장](RULES.md#11-도메인업무-규칙) | 초안 |
| 선택 규칙(화주별) 목록과 설정 파일 형식 | [RULES.md 11-11](RULES.md#11-11-화주별-특이-규칙), `backend/rules/` | 초안 |
| SAMC 운영 중인 자동화 코드와의 연계 방안 | [AGENTS.md 1장](AGENTS.md#1장-기능-목록과-상태)(기존 도구 대응), `docs/handover/연계방안.md` | 예정 |
| 설치·키 설정 방법 | `docs/handover/설치.md` | 예정 |
| 사용 방법(담당자용) | `docs/handover/사용방법.md` | 예정 |
| 화주 추가 방법 | `docs/handover/화주추가.md` | 예정 |
| 성과지표 결과 | `docs/handover/성과지표.md` | 2주차 |
| Windows 실행 파일(exe) | 릴리스 | 마지막 단계 |

## 기존 도구와의 관계

SAMC가 지금 쓰는 자동화 도구(구글 시트 + Python)가 기준선입니다. 그 안의 검증된 로직(실적 선택, 제조사 주소 매칭, 신고건 묶음, 품목사항 양식)은 옮겨 쓰고, 구글 시트 대신 우리 화면, 코드 속 화주 규칙 대신 설정 화면, Gemini 대신 Claude·GPT로 바꿉니다. 기존 도구 원본과 실제 화주 자료는 이 저장소에 넣지 않습니다.
