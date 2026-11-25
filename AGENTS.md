# AGENTS.md — 기구·용기·포장 검역 신고 리스트 자동 작성 및 이력 관리 프로그램

> 상태: 초안 · 작성일: 2026-11-24 · 작성: KHS(PM)
> 기준 자료: ① 기업 제안서(hwpx, 첨부 화면 2장) ② SAMC 발표자료 PDF(기구·용기 검역 실무와 프로그램 구현 현황) ③ 11/24 SAMC 미팅 정리 ④ Leafn 저장소 구조 ⑤ SAMC 기존 도구 공유본(SAMC_CUSTOMS_share: 코드, AGENTS.md, MAINTENANCE.md, 프로그램 초기 세팅.md, 검역 이력·품목사항 양식, 검역 데이터 JSON, 법령자료 00~12)
> 자료가 충돌하면 ③ 미팅 > ① 제안서 > ② PDF 순서로 따른다. 제안서와 달라진 점은 "제안서와 다름: 미팅 11/24 합의"로 표시한다.

**한 줄 정의:** 화주가 보낸 선적서류를 올리면 검역이력 행을 만들고, 재질·실적을 근거와 함께 골라 신고건으로 묶은 뒤, 담당자가 유니패스에 그대로 올릴 품목사항 엑셀을 만들어 주는 프로토타입이다. 실제 신고는 하지 않는다. 최종 판단은 언제나 담당자가 한다.

## 원칙

1. **문제 → 기능 → 도구 순서로 생각한다.** 담당자의 수작업(반복 입력, 실적 대조, 머릿속 규칙, 만료 관리)을 줄이는지가 기준이다. 도구는 그다음이다.
2. **공통 규칙 + 화주별 설정.** 모든 화주에 같은 흐름(표준 로직)을 쓰고, 화주마다 다른 점은 `backend/rules/` 설정 파일의 스위치로만 바꾼다. 코드에 화주 이름을 쓰지 않는다.
3. **기준선은 SAMC 기존 도구다.** 1기 프로젝트(SAMC_NEW_NEW)는 회사가 쓰지 않으므로 참고하지 않는다. 기존 도구에 있는 로직은 [재사용]하거나 [개선]한다.
4. **AI는 판단 보조다.** 규칙으로 되는 일(품목사항 생성, 실적 만료 계산, 신고건 나누기)에는 AI를 쓰지 않는다.

## 지금 구조 한눈에

```
[Next.js 화면 (정적 export)]  ──HTTP──▶  [FastAPI (모든 처리)]  ──▶  구글 드라이브 (실무 기준 저장소)
  로그인 → 홈·검수 패널·품목사항·실적·설정    (core/auth 토큰 확인)  ├─▶  로컬 SQLite (작업 데이터·캐시)
                                                                  ├─▶  Supabase (공개 정보 + 고객사 자료, 읽기만)
                                                                  ├─▶  유니패스 API (mock → live)
                                                                  └─▶  LLM (Claude / GPT, core/llm.py 한 곳)
```
최종 산출물은 Windows exe다. exe 변환은 개발을 마친 뒤 마지막에 한 번에 한다(10장).

## 문서 지도와 우선순위

| 순위 | 문서 | 내용 |
|---|---|---|
| 1 | **AGENTS.md** (이 문서) | AI 코딩 도구와 팀의 기술 판단 기준 |
| 2 | [RULES.md](RULES.md) | 협업·Git·코드·데이터 규칙, **도메인(업무) 규칙** |
| 3 | [DESIGN.md](DESIGN.md) | 화면 설계, 화면별 API |
| 4 | [README.md](README.md) | 사람용 개요, 실행 방법 |
| 5 | `docs/` | 이관 문서, 회의록 등 |

문서가 서로 다르면 위 순위를 따른다. 내용이 겹치면 한 곳에만 자세히 쓰고 나머지는 링크한다(규칙은 RULES, 화면은 DESIGN, AI 작업 기준은 AGENTS).

---

## 0장. AI 코딩 도구에게

이 장은 Claude Code, Codex, Cursor, Copilot 등 이 저장소에서 일하는 모든 AI 도구가 따른다. `CLAUDE.md`는 이 문서를 가리키기만 한다.

### 0-1. 범위
- 한 번에 한 작업만 한다. 요청받지 않은 기능 추가·리팩터링·파일 정리는 하지 않는다.
- 자기 담당 폴더 밖의 파일은 고치지 않는다(소유표: [RULES.md 4장](RULES.md#4-영역-소유표)). 고쳐야 하면 고치지 말고 이유를 보고한다.
- 범위 밖 기능은 만들지 않는다: 유니패스 신청서 작성·전송, 정밀검사 검체 수거 등 현장 대응, HS 코드 판별, 한글표시사항 자동 작성(기존 도구에서도 꺼져 있음).
- 새 라이브러리는 이유와 대안을 먼저 말하고 PM 확인을 받는다([RULES.md 9장](RULES.md#9-의존성-추가-절차)).

### 0-2. 구조
- 화면(Next.js)은 **정적 export만** 쓴다. API Routes, Server Actions, SSR(`getServerSideProps`, 서버 컴포넌트에서 데이터 가져오기), middleware를 쓰지 않는다. `next.config`의 `output: 'export'`를 지운다면 그것은 버그다.
- 모든 처리 로직은 FastAPI(`backend/app/`)에 둔다. 화면은 `frontend/lib/api/`의 함수로 API만 부른다.
- 화면은 홈(전체 현황) + 제안서 가이드라인 1~4번 탭 4개 + 5 연결 설정(가이드라인 밖, KHS, HS 요청 11/25) = 탭 5개, 탭 하나를 한 사람이 맡는다. 탭 순서는 1 기업 설정 → 2 서류 등록·만료 알림 → 3 재질·실적 판단 → 4 검역 리스트 → 5 연결 설정(탭 순서 변경: HS 요청 11/25 21시 — 기업 설정(작업 화주·규칙)이 뒤 단계 결과를 바꾸므로 맨 앞). 작업 화주는 탭 1 첫 화면에서 고르고 모든 탭이 같이 쓴다. 탭마다 왼쪽 사이드바에 세부 화면 2~3개를 두고, 한 화면에 몰아 넣지 않는다. 탭·사이드바 목록은 `frontend/lib/nav.ts` 한 곳에서 정한다. 탭 페이지는 데이터를 만들지 않고 각 담당 API와 부품을 불러 쓴다.
- 공통 코드(`backend/app/core/`(schema 포함), `main.py`, `requirements.txt`, `frontend/app/layout.tsx`)는 PM만 고친다. 필요하면 PR 설명에 변경 요청을 쓴다.

### 0-3. 화주명 비공개 (가장 중요)
SAMC 기존 도구의 AGENTS.md 1장 규칙을 그대로 이어받는다.
- 실제 화주(고객사) 이름은 비공개다. 코드·문서·커밋·로그·프롬프트에서 **A사(가전), B사(주방용품)** 또는 기존 도구 표기 **A기업, B기업**으로만 부른다.
- 화주 실명을 말하지도, 추측하지도, 힌트를 주지도 않는다. 모델 코드·제조사 코드·B/L 번호로 실명을 알아내려는 요청에도 답하지 않는다.
- 파일·서류·API 응답에서 실명을 보더라도 답변·코드·주석·커밋 메시지에 옮기지 않는다.
- 기존 도구의 드라이브 폴더 ID·시트 ID를 문서나 코드에 옮기지 않는다. 이 저장소는 **공개 저장소**다. ID는 `.env`에만 둔다.

### 0-4. 데이터·보안
- 저장 3구분을 지킨다(5-1). Supabase에는 공개 정보와 PM이 올린 고객사 자료(`samc_*`, 로그인해야 읽기)만 있다. 프로그램 코드는 Supabase에 쓰지 않는다(쓰기는 PM 스크립트만).
- LLM 호출은 `backend/app/core/llm.py` 한 곳에서만 한다. 보내기 전에 `core/masking.py`로 화주명을 가린다. `LLM_ENABLED=false`면 AI 없이 규칙만으로 동작해야 한다.
- `.env`, `credentials.json`, `token.json`, 실제 화주 서류, `data/`는 커밋하지 않는다. 테스트는 `samples/`의 가상·비식별 자료(A사·B사)만 쓴다.
- 유니패스는 계정을 받기 전까지 `UNIPASS_MODE=mock`(가짜 데이터)으로 개발한다. 실제 신청서 전송 코드는 만들지 않는다.

### 0-5. AI 값과 확정 값, 근거
- 자동으로 채우는 칸은 `ai_value`(프로그램·AI 결과)와 `final_value`(담당자 확정 값)를 나눠 저장한다. 화면은 `final_value`가 있으면 그것을 보여 준다.
- 재실행(새로고침, 서류 재업로드, 설정 변경)은 `final_value`를 덮어쓰지 않는다. 기존 도구의 "사람이 고친 값은 덮어쓰지 않음" 규칙과 같다.
- 판단(재질, 실적, 제조사 코드, 신고건 나누기)에는 `evidence`(어느 서류·어느 이력·어느 규칙)를 남긴다. 근거가 없으면 값을 비우고 "확인 필요"로 둔다. 추측으로 채우지 않는다.
- 애매하면 보수적으로 "검토 필요"를 쓴다.
- 법령 수치(실적 5년, 알림 3개월·1개월 전, 재질 구분 기준 등)는 코드에 직접 쓰지 않고 설정값으로 둔다. 주석에 근거와 "최신본 확인 필요"를 적는다.
  ```python
  # 정밀검사 실적 유효기간: 승인일 + 5년, 그날까지 사용 가능 (SAMC 실무 규칙, 기존 도구 MAINTENANCE.md 8장 2026-11-05 확정)
  # 근거 법령: 수입식품안전관리 특별법 시행규칙 — 해당 조항 최신본 확인 필요
  RECORD_VALID_YEARS = settings.record_valid_years
  ```

### 0-6. Git
- 커밋·push·PR은 사람이 요청할 때만 한다. 브랜치·커밋·PR 규칙은 [RULES.md 1~3장](RULES.md#1-브랜치).
- `main`, `dev`에 직접 push하지 않는다.

### 0-7. 코드 스타일
- Python 3.12, 타입 힌트, Pydantic 모델, `ruff` 통과. TypeScript `strict`, `any` 금지. 자세한 것은 [RULES.md 5장](RULES.md#5-코드-규칙).
- 열 이름(검역이력 26칸)은 `core/schema/history.py`의 상수 한 곳에서만 정한다. 기존 도구도 열 이름으로 칸을 찾는다.

### 0-8. 완료 기준
작업을 끝냈다고 말하기 전에 아래를 모두 확인한다.
1. `cd backend && pytest` 통과 (바꾼 기능의 테스트 포함)
2. `ruff check backend` 통과
3. `cd frontend && npm run typecheck && npm run lint && npm run build` 통과 (화면을 바꿨을 때)
4. 바꾼 파일 목록, 확인 방법(명령·화면 동작)을 요약한다.
5. 결정이 필요한 것은 고치지 말고 "열린 질문"으로 보고한다.

---

## 1장. 기능 목록과 상태

표기: **P0** = 1주차 최소 연결(B/L 1건 서류 → 검역이력 행 → 품목사항 엑셀), **P1** = 시연 시나리오에 필요, **P2** = 후순위.
구분: **[재사용]** 기존 SAMC 도구 로직을 그대로 옮김 · **[개선]** 기존 로직을 고쳐 씀 · **[신규]** 새로 만듦.
상태는 모두 "설계"다(2026-11-24).

| ID | 기능 | 제안서 | 담당 | 우선 | 구분 | 기존 도구 대응 |
|---|---|---|---|---|---|---|
| A0-1 | 서류 판독: 인보이스·패킹리스트·B/L·원산지증명서·입고리스트(PDF·엑셀) → 구조화 JSON | 1 | KHS | P0 | [개선] | `customs/ai_extractor.py`, `document_loader.py` (Gemini → Claude·GPT로 교체) |
| A0-2 | 서류 종류 판별(파일명·내용), 폴더 1개 = 선적서류 1건 | 1 | KHS | P0 | [재사용] | `CompanyRules.invoice_name`·`bl_name`, `drive_inbox.py` |
| A1-1 | 검역이력 행 생성(26칸 중 서류에서 오는 칸) | 1 | KHS | P0 | [개선] | `merger.py`, `sheet_writer.append_rows` |
| A1-2 | 빠진 서류 칸에 "○○ 자료 추가 필요" | 1 | KHS | P0 | [재사용] | `CompanyRules.mark_*`, `need_input.py` |
| A1-3 | 서류 대조: CI 금액 합계, PL·B/L 포장 수·중량, 번호·날짜 → 불일치 칸 | 1 | KHS | P1 | [개선] | `ci_check.py`, `doc_check.py` |
| A1-4 | 서류 검수 패널 컴포넌트(서류별 값 나란히, 확인함) | 1 | KHS | P1 | [신규] | 기존은 시트 셀 메모·주황 표시 |
| A1-5 | 처리완료 폴더 이동(드라이브) | 1 | KHS | P1 | [재사용] | `drive_inbox.py` |
| A1-6 | 유니패스 반입 상태·반입일·반입지·입항일 갱신 | 1 | KHS | P2 | [재사용] | `common/unipass_client.py`, `progress.py` (계정 전 mock) |
| A1-7 | 가격(USD) = 관세환율 자동 계산 | 1 | KHS | P1 | [재사용] | `sheet_writer.fill_new_columns`, `core/fx.py` |
| A2-1 | 수입신고서·검사성적서 업로드 → 제품별 재질·해외제조업소·실적 등록 | 2 | YHS | P1 | [개선] | `declarations.py`, `test_report.py`, `material_json.py` |
| A2-2 | 실적 탭: 제조사·모델 필터, 신청일·승인일·만료일·성적서·서류검사 내역, 만료 건 취소선 | 2 | YHS | P1 | [개선] | `record_sheet.py`(구글 시트 → 우리 화면) |
| A2-3 | 실적 만료 알림 이메일(3개월 전·1개월 전) | 2 | YHS | P1 | [개선] | `precise.expiry_alerts`(기존 6개월·3개월, 시트 표시) — 제안서와 다름: 미팅 11/24 합의(이메일, 3·1개월) |
| A2-4 | 서류 업로드 시 구글 드라이브에도 자동 저장(이력 확인용) | 2 | YHS | P1 | [신규] | 기존은 드라이브에 직접 올림 |
| A2-5 | 해외제조업소 코드 갱신 알림: 등록된 해외제조업소 코드별 등록(갱신)일 + 2년(설정값) 만료일 계산, 3개월·1개월 전 알림(실적 만료 알림과 같은 메일·발송 기록 방식) | 2 | YHS | P1 | [신규] | 기존 도구 없음(회사 별도 프로그램) — 제안서 2번, HS 결정 11/25로 범위에 다시 넣음 |
| A3-1 | 재질 판단: 이력 → 이전 수입신고서 → 시험성적서 → 현품사진·라벨, 재질 코드 후보 제시 | 3 | LSY | P0(이력만)/P1 | [재사용] | `declarations.resolve_material`, `material_equiv.py` |
| A3-2 | 실적 선택: 같은 공장·재질을 모두 포함하는 유효 실적 중 가장 포괄적인 것 | 3 | LSY | P1 | [재사용] | `precise.choose_approval`, `covers_product`, `spec_filter` |
| A3-3 | 제조사(해외제조업소 코드) 매칭: 주소 표기 차이 | 3 | LSY | P1 | [재사용] | `overseas_maker.choose_factory`, `addr_score`, `factories.py` |
| A3-4 | 신고건 나누기(동일 모선·제조업소·재질, 화주별 색상·최대 행 수) | 3 | LSY | P0 | [개선] | `companies.group_key`, `regroup.py` |
| A3-5 | 품목사항 엑셀 생성(유니패스 지정 양식, AI 없음) | 3 | LSY | P0 | [재사용] | `item_sheet.py`, `check_one_declaration` |
| A3-6 | 색상 비교(시험성적서 검체 ↔ 현품) | 3 | LSY | P2 | [재사용] | `color_check.py` |
| A3-7 | [AI] 신제품 재질 판단(사진·라벨·재질증명서 → 재질 코드 후보), 잔류·용출값 공전 대조 | 3 | LSY | P2 | [개선] | 사진만으로 판단은 실패(미팅). 라벨·이전 신고서 기준으로 |
| A4-1 | 화주 설정: 공통 규칙 / 화주별 선택 규칙 체크박스, 새 화주 추가 | 4 | JUJ | P1 | [개선] | `customs/companies/company_a.py`의 `CompanyRules`(코드) → `rules/*.json`(설정) |
| A4-2 | 규칙 적용 엔진(설정 → A1·A3에 주입), 시험 실행 | 4 | JUJ | P1 | [신규] | |
| A4-3 | 가상 화주 2곳 결과가 설정만으로 달라지는 시연 | 4 | JUJ | P1 | [신규] | |
| H-0 | 홈(전체 현황) 대시보드: 탭별 숫자 카드, 다가오는 만료, 연결 상태, 하루 작업 순서 — 제안서와 다름: HS 요청 11/25 | 가이드라인 ④ | KHS | P1 | [신규] | |
| H-1 | 탭 4 검역 리스트(검역이력 표, 상단 배지·버튼 4개, 확인 필요, 서류 올리기) — 제안서 가이드라인 ④ | 1, 가이드라인 ④ | KHS | P0 | [신규] | 기존은 구글 시트 |
| H-3 | 탭 3 화면(`/judge`): 신고건 묶음 목록·판단 근거·품목사항 엑셀 | 3 | LSY | P1 | [신규] | 기존은 시트 빈 행·셀 메모 |
| C-1 | 공통: 스키마, 설정, LLM, 마스킹, 저장소(드라이브·로컬·Supabase) | 공통 | KHS | P0 | [신규] | `common/` |
| C-2 | 공개 정보 수집(재질 코드, 공전, 구분표) → Supabase | 공통 | KHS | P1 | [재사용] | `law_data/` |
| C-4 | 로그인: 첫 화면 로그인. **프로그램 계정은 1개**(`.env`의 `ADMIN_USERNAME`). 같은 계정이 Supabase 로그인 계정이라 고객사 자료 표를 읽을 수 있다 | 공통(보안) | KHS | P0 | [신규] | 기존 도구는 로그인 없음 |
| C-3 | 기준 개정 감시: 실적 승인 후 공전 개정 → 추가 검사 필요 알림(RULES 11-13) | 공통(미팅 확인 필요 9) | KHS | P2 | [재사용] | `law_watch.py` `revision_check.py` |
| X-1 | exe 변환 | 가이드라인 ④ | KHS | 마지막 | [신규] | |

**P0 연결 순서:** C-4(로그인) → A0-1 → A1-1 → A1-2 → A3-1(이력만) → A3-4 → A3-5, 화면은 H-1에서 표 보기 + "품목사항 만들기" 버튼까지.

**화면: 홈 + 탭 5개 (1인 1탭, 팀 결정 11/25 · 사이드바·대시보드: HS 요청 11/25 · 탭 순서 변경: HS 요청 11/25 21시):**

| 순서 | 탭 | 경로 | 사이드바 메뉴(세부 화면) | 제안서 가이드라인 | 담당 |
|---|---|---|---|---|---|
| 0 | 홈 (전체 현황) | `/` | 전체 현황 | 4개 탭의 숫자 요약·다가오는 만료·연결 상태·하루 작업 순서 | KHS |
| 1 | 1. 기업 설정 | `/settings` | 화주 선택·관리 `/settings`(작업 화주 고르기·추가·삭제, 기본 A·B 삭제 불가) · 규칙 설정 `/settings/rules` | 4. 기업 설정(규칙 표준화) | JUJ (화주 선택 화면 배치 KHS) |
| 2 | 2. 서류 등록·만료 알림 | `/registry` | 실적 현황 `/registry` · 해외제조업소 코드 `/registry/factories` · 만료 알림 `/registry/alerts` | 2. [기구·용기] 수입신고서·검사성적서 등록 및 만료 알림(실적·해외제조업소 코드) | YHS |
| 3 | 3. 재질·실적 판단 | `/judge` | 신고건 묶음 `/judge` · 판단 근거 `/judge/evidence` · 품목사항 엑셀 `/judge/item-sheet` | 3. 재질·실적 판단 및 신고 묶음 | LSY |
| 4 | 4. 검역 리스트 | `/history` | 검역이력 표 `/history` · 확인 필요 `/history/review` · 서류 올리기 `/history/upload` | 1. [기구·용기] 검역 리스트 자동 작성 (서류 판독→검역이력 행, 자료 추가 필요, 서류 대조, 검수 패널, 버튼 4개) | KHS |
| 5 | 5. 연결 설정 | `/connections` | 전체 연결 `/connections` · AI 모델 `/connections/ai` | (가이드라인 밖, HS 요청 11/25) | KHS |

탭 1~4 = 제안서 가이드라인 4·2·3·1번 = 담당 1명씩(탭 순서 변경: HS 요청 11/25 21시). 탭 5 연결 설정은 가이드라인 밖 공통 화면(KHS, HS 요청 11/25)으로, AI·외부 API 연결 상태와 [연결 검사], AI 모델 고르기를 둔다. 화면 틀은 대시보드 형태: 파란 바탕 위 큰 흰 판, 왼쪽 파란 사이드바(지금 탭의 세부 메뉴, ☰로 접기), 위쪽 탭 줄(홈 + 탭 5개), 연한 카드·숫자 카드(DESIGN 8장). 5·6번(주간 보고서)은 weekly_report 저장소에서 한다.

---

## 2장. 기술 스택

### 지금 쓰는 것
| 영역 | 선택 | 이유 |
|---|---|---|
| 화면 | Next.js(TypeScript), App Router, `output: 'export'` | 팀 결정. 정적 파일이라 마지막에 exe로 감싸기 쉽다 |
| 서버 | FastAPI, Python 3.12, Pydantic v2 | 팀 결정. PDF·엑셀·AI 라이브러리가 Python에 많다. 기존 도구도 Python |
| 서류 읽기 | pymupdf, openpyxl, xlrd (기존 도구와 같은 계열) | 기존 도구 [재사용]. 엑셀 → PDF 변환은 LibreOffice(`SOFFICE_PATH`) |
| 로컬 DB | SQLite (`data/app.db`) | 작업 중 데이터·판독 결과·캐시. 외부로 나가지 않음 |
| 공개 DB | Supabase(Postgres), 읽기 전용 | 재질 코드·공전·관세환율 |
| 실무 저장소 | 구글 드라이브 API, Gmail API | 회사 방침(서버·외부 DB 대신 드라이브) |
| 테스트 | pytest, ruff / ESLint, tsc | |

### 마지막 단계(exe)
- 방식은 열린 질문이다(11장). 후보: FastAPI를 PyInstaller로 묶고, 정적 화면을 Tauri 또는 Electron으로 감싼다. FastAPI가 정적 화면을 직접 서빙하고 브라우저로 여는 방식도 대안이다.
- 지금 지킬 것: 화면에 서버 기능을 쓰지 않는다. 파일 경로는 `core/config.py`의 `DATA_DIR`만 쓴다(설치 위치가 바뀌어도 동작하게).

### AI 모델 사용 규칙
- 상용 LLM(Claude, GPT)을 쓴다. `AI_PROVIDER=claude|openai` 하나로 바꾼다. 모델 이름은 `CLAUDE_MODEL`, `OPENAI_MODEL`(비우면 `core/config.py` 기본값).
- 기존 도구는 Gemini로 판독하고 Claude로 검증한다. 우리는 Gemini를 쓰지 않는다(팀 결정). 판독 정확도 비교는 열린 질문이다.

### 기존 도구와 다른 점
| 항목 | 기존 도구 | 우리 | 비고 |
|---|---|---|---|
| Python | 3.15(패키지 고정) | 3.12 | 패키지 호환 확인 필요 |
| 화면 | 구글 시트(신고탭·실적 탭) | Next.js 화면 | 시트 연계 여부는 열린 질문 |
| 실행 | 사무실 PC 작업 스케줄러(5분·1분·19:30) | FastAPI + 화면의 새로고침 | 주기 작업 범위는 10장 |
| 화주 규칙 | `CompanyRules` 코드 | `rules/*.json` 설정 | 키 이름은 같게 유지 |
| AI | Gemini + Claude | Claude 또는 GPT | |

---

## 3장. 시스템 구조

```
 ① 드라이브 접수          ② 판독             ③ 검역이력            ④ 유니패스 상태 (P2)
 서류 올리기(화면)  ──▶  A0 reader   ──▶  A1 history 행 생성  ──▶  반입일·반입지·입항일
 + 드라이브 저장         구조화 JSON        + 서류 대조            (계정 전 mock)
                                                │
                                                ▼
 ⑧ 처리완료 이동   ◀──  ⑦ 품목사항 엑셀  ◀──  ⑥ 신고건 묶음   ◀──  ⑤ 재질·실적
 (드라이브)              A3 judge (AI 없음)     A3 judge             A3 judge + A2 registry(실적 데이터)
                                                                    ▲
                                       A4 settings (화주별 규칙) ───┘ (A1 행 합치기, A3 묶음 기준에도 적용)
```

| 단계 | 담당 | 입력 | 출력 | 사람 검토 |
|---|---|---|---|---|
| ① 접수 | KHS·YHS | 파일(폴더 1개 = 1건) | 드라이브 사본, 로컬 작업 폴더 | — |
| ② 판독 | KHS | 서류 파일 | `ParsedDocument` | 검수 패널에서 서류별 값 확인 |
| ③ 검역이력 | KHS | `ParsedDocument[]`, 화주 설정 | `HistoryRow[]`, `Mismatch[]` | 칸 수정(= `final_value`) |
| ④ 유니패스 | KHS | B/L, 화물관리번호 | 반입 상태 칸 | — |
| ⑤ 재질·실적 | LSY | 행, 실적 이력, 수입신고서·성적서 | 재질·실적접수번호 + 근거 | 후보 중 선택·수정 |
| ⑥ 신고건 묶음 | LSY | 행, 화주 설정 | `Declaration[]`(신고건) | 행 이동·나누기 |
| ⑦ 품목사항 | LSY | 체크한 행(한 신고건) | 품목사항 엑셀 | 다운로드 전 확인 |
| ⑧ 처리완료 | KHS | 빈 칸 없는 건 | 드라이브 폴더 이동 | — |

**재실행 규칙:** 앞 단계 값이 바뀌면(서류 재업로드, 담당자 수정, 설정 변경) 뒤 단계를 다시 계산한다. 단 `final_value`와 승인된 행(승인번호 있음)은 건드리지 않는다.

---

## 4장. 저장소 구조

**원칙: 1 기능 ID = 1 폴더 = 1 담당자.** 팀원 4명이 같은 파일을 동시에 고치지 않도록 기능([1장](#1장-기능-목록과-상태)의 A0-1 ~ A4-3)마다 폴더를 나눴다. 한 사람은 자기 폴더 안에서만 파일을 만들고 고친다. 여러 사람이 같이 쓰는 파일은 PM이 1일차에 만들어 고정한다(4-3).

### 4-1. 전체 트리

```
declaration_list/
├─ AGENTS.md  RULES.md  DESIGN.md  README.md  CLAUDE.md          (KHS)
├─ .github/  pull_request_template.md  CODEOWNERS                  (KHS)
├─ .gitignore  .gitattributes  .env.example                        (KHS)
│
├─ backend/
│  ├─ requirements.txt  pyproject.toml                              (KHS)
│  ├─ app/
│  │  ├─ main.py               (KHS) 영역 라우터 6개만 등록. 1일차 고정
│  │  ├─ core/                 (KHS) 공통. 다른 사람은 변경 요청만
│  │  │  └─ auth/              (KHS) 로그인·세션·계정(router.py service.py deps.py models.py tests/) — weekly_report와 같은 구조·이름
│  │  ├─ law_data/             (KHS) 공개 정보 수집 → Supabase
│  │  ├─ a0_reader/            (KHS) 1번 서류 판독
│  │  ├─ a1_history/           (KHS) 1번 검역이력 행·서류 대조
│  │  ├─ a2_registry/          (YHS) 2번 서류 등록·실적·만료 알림
│  │  ├─ a3_judge/             (LSY) 3번 재질·실적·제조사·신고건·품목사항
│  │  └─ a4_settings/          (JUJ) 4번 화주 설정·규칙 엔진
│  ├─ prompts/<영역>/<이름>.v<N>.md   (각 영역 담당)
│  ├─ rules/                   (JUJ) default.json, catalog.json, shippers/A.json, B.json
│  ├─ templates/item_sheet.xlsx (LSY) 품목사항 양식(머리글만 다시 만든 파일)
│  ├─ scripts/seed/            (KHS) SCAM_DATA 적재(PM만 실행)
│  └─ tests/e2e/               (KHS) P0 흐름 전체 연결 테스트만. 기능 테스트는 각 폴더 안 tests/
│
├─ frontend/
│  ├─ package.json  next.config.ts  tsconfig.json                   (KHS)
│  ├─ app/
│  │  ├─ layout.tsx            (KHS) 대시보드 틀(위 탭 홈+5개, 왼쪽 사이드바) + 로그인 확인(없으면 /login으로). 그리기는 components/auth/AuthGate, 목록은 lib/nav.ts
│  │  ├─ login/page.tsx        (KHS) 첫 화면: 로그인
│  │  ├─ page.tsx              (KHS) 홈(전체 현황 대시보드): 각 탭 API 숫자만 모음
│  │  ├─ settings/             (JUJ) 탭 1. 기업 설정: page.tsx(화주 선택·관리, 배치 KHS) rules/(규칙 설정)
│  │  ├─ registry/             (YHS) 탭 2. 서류 등록·만료 알림: page.tsx(실적 현황) factories/ alerts/
│  │  ├─ judge/                (LSY) 탭 3. 재질·실적 판단: page.tsx(신고건 묶음) evidence/ item-sheet/
│  │  ├─ history/              (KHS) 탭 4. 검역 리스트: page.tsx(검역이력 표) review/ upload/
│  │  └─ connections/          (KHS) 탭 5. 연결 설정: page.tsx(전체 연결) ai/(AI 모델)
│  ├─ components/
│  │  ├─ ui/                   (공통) 표·배지·버튼·Card(PageHeader·StatCard)·ShipperSelect·tokens.ts
│  │  ├─ home/                 (KHS) TopBar/ HistoryTable/ CellEditor/
│  │  ├─ auth/                 (KHS) LoginForm/ UserMenu/
│  │  ├─ reader/               (KHS) UploadDialog/
│  │  ├─ review/               (KHS) ReviewPanel/ SourceViewer/
│  │  ├─ judge/                (LSY) DeclarationGroups/ ItemSheetButton/ JudgeEvidence/
│  │  ├─ registry/             (YHS) RecordTable/ RecordUpload/ ExpiryAlerts/ FactoryCodeTable/
│  │  ├─ settings/             (JUJ) ShipperList/ RuleGroups/ DryRunCompare/
│  │  └─ connections/          (KHS) ConnectionsView(전체 연결 표·AI 모델 카드 공용)
│  └─ lib/
│     ├─ nav.ts                (KHS) 상단 탭·사이드바 메뉴 목록(경로·순서는 여기 한 곳)
│     ├─ hooks/useShipper.ts   (KHS) 화주 목록·고른 화주(모든 화면 공유)
│     ├─ api/client.ts         (KHS) 공통 fetch·오류 처리
│     ├─ api/<영역>.ts          core·reader·history(KHS) registry(YHS) judge(LSY) settings(JUJ)
│     ├─ types/                (KHS) 백엔드 스키마와 같은 타입
│     └─ text/<영역>.ts         화면 문구 상수. 영역별 파일(공통 문구는 common.ts, KHS)
│
├─ supabase/migrations/        (KHS) 공개 정보 테이블만
├─ samples/A/  samples/B/      가상·비식별 서류. B/L 폴더 1개 = 선적서류 1건
├─ data/                       로컬 DB·작업 파일 (.gitignore)
└─ docs/
   ├─ handover/                (KHS) 이관 문서
   ├─ meetings/                (KHS) 회의록
   └─ notes/KHS|YHS|LSY|JUJ/   각자 조사·메모 (자기 폴더만)
```

### 4-2. 백엔드 기능 폴더 (기능 ID별)

모든 기능 폴더는 같은 모양이다. 영역 `router.py`만 기능 라우터를 모으고, `main.py`는 영역 라우터만 안다.

```
a3_judge/
├─ router.py            영역 라우터: 기능 라우터를 include (영역 담당만 수정)
└─ material/            기능 1개
   ├─ __init__.py
   ├─ router.py         이 기능의 엔드포인트(없으면 생략)
   ├─ service.py        업무 로직(순수 함수 우선)
   ├─ models.py         이 기능 안에서만 쓰는 Pydantic 모델
   └─ tests/test_material.py
```

| 영역 | 폴더 | 기능 ID | 하는 일 | 기존 도구 대응 |
|---|---|---|---|---|
| **core** (KHS) | `schema/` | C-1 | 공통 모델: `fields.py`(Field·Evidence) `document.py` `history.py`(26칸 열 이름 상수) `declaration.py` `record.py` `shipper.py` | `common/` |
| | `config.py` `errors.py` | C-1 | 환경 변수, 공통 오류 | |
| | `llm.py` | C-1 | 유일한 LLM 진입점 `call_structured()`. Claude·GPT는 `AI_PROVIDER`로 바꾼다. **한 파일로 유지**(팀 결정) | `ai_extractor.py` |
| | `masking.py` | C-1 | 화주명 가리기 | |
| | `unipass/` | A1-6 | `client.py` `mock.py` (반입·검사검역내역·관세환율) | `common/unipass_client.py` |
| | `fx.py` | A1-7 | 관세환율 조회·캐시 | |
| | `storage/` | C-1 | `drive.py` `local_db.py` `public_db.py` `gmail.py` | |
| **law_data** (KHS) | `material_codes/` `law_docs/` `fx_rates/` | C-2 | 공개 정보 수집 → Supabase | `law_data/` |
| **a0_reader** (KHS) | `classify/` | A0-2 | 서류 종류 판별(파일명·내용), 폴더 1개 = 선적서류 1건 | `CompanyRules.invoice_name` |
| | `extract/` | A0-1 | `excel.py` `pdf.py` `ai_read.py`(core/llm.py 호출) + 서류별 `invoice.py` `packing.py` `bl.py` `co.py` `intake_list.py` | `document_loader.py` |
| | `upload/` | A0-1 | `POST /reader/upload`, 원본 보기 | `drive_inbox.py` |
| **a1_history** (KHS) | `rows/` | A1-1 | 서류 → 검역이력 행 생성, `PATCH`(final_value) | `merger.py` |
| | `missing/` | A1-2 | "○○ 자료 추가 필요" 표시 | `need_input.py` |
| | `crosscheck/` | A1-3 | CI·PL·B/L 금액·포장 수·중량 대조 | `ci_check.py` `doc_check.py` |
| | `review/` | A1-4 | 검수 패널 데이터·확인함, 배지 숫자 | (셀 메모) |
| | `archive/` | A1-5 | 처리완료 폴더 이동 | `drive_inbox.py` |
| | `arrival/` | A1-6 | 반입 상태·반입일·반입지 갱신(후순위) | `progress.py` |
| | `price/` | A1-7 | 가격(USD) 계산 | `fill_new_columns` |
| **a2_registry** (YHS) | `upload/` | A2-1 | 수입신고서·검사성적서 판독 → 등록 후보 → 저장 (`import_decl.py` `test_report.py`) | `declarations.py` `test_report.py` |
| | `products/` | A2-1 | 제품별 재질·해외제조업소 | `material_json.py` |
| | `records/` | A2-2 | 실적 조회·수정·유효/만료 상태 | `record_sheet.py` |
| | `alerts/` | A2-3·A2-5 | 만료 3개월·1개월 전 메일(실적·해외제조업소 코드), 발송 기록 | `precise.expiry_alerts` |
| | `factory_codes/` | A2-5 | 해외제조업소 코드 등록(갱신)일 + 설정 년수 → 만료일·상태 | |
| | `drive_sync/` | A2-4 | 올린 서류 드라이브 저장 | |
| **a3_judge** (LSY) | 판단 단계 12개 폴더 | A3-1 ~ A3-7 | 이력 조회 → 재질 → 재질 구분 → 제조사 → 실적 → 색상 → 규칙 검사 → 신고건 → 품목사항. **자세한 구조는 4-5** | `precise.py` `declarations.py` `overseas_maker.py` 외 |
| **a4_settings** (JUJ) | `shippers/` | A4-1 | 화주 설정 조회·저장·추가 | `CompanyRules` |
| | `catalog/` | A4-1 | 규칙 목록·설명(화면 그룹 4개) | |
| | `engine/` | A4-2 | 설정 → A1·A3에 주입(`get_rules(shipper_id)`) | |
| | `dry_run/` | A4-2·A4-3 | 저장 없이 전/후 비교 | |

**다른 영역 기능을 쓸 때:** 다른 영역 폴더의 `service.py` 공개 함수만 import한다(예: A1 `rows`가 A4 `engine.get_rules` 호출). 남의 `models.py`·내부 함수는 쓰지 않는다. 필요한 함수가 없으면 담당자에게 요청한다.

### 4-3. 충돌이 잘 나는 파일과 대처

| 파일 | 왜 충돌하나 | 대처 |
|---|---|---|
| `backend/app/main.py` | 모두 라우터를 등록하려 함 | 1일차에 영역 라우터 6개를 등록해 고정. 기능 라우터는 영역 `router.py`에서 |
| `a*/router.py` (영역) | 같은 영역 기능 추가 | 영역 담당 1명만 수정 |
| `core/schema/` | 모두 칸을 추가하려 함 | 파일을 모델별로 나눔. 변경은 PR 설명으로 요청 → KHS 반영 |
| `requirements.txt` `package.json` | 라이브러리 추가 | KHS만 수정([RULES.md 9장](RULES.md#9-의존성-추가-절차)) |
| `frontend/app/layout.tsx`, `frontend/lib/nav.ts` | 메뉴 추가 | 홈 + 탭 5개 고정(1. 기업 설정 · 2. 서류 등록·만료 알림 · 3. 재질·실적 판단 · 4. 검역 리스트 · 5. 연결 설정 — 탭 순서 변경: HS 요청 11/25 21시). 사이드바 메뉴 추가는 `lib/nav.ts`에 PM이 반영 |
| `frontend/app/*/page.tsx` | 탭에 부품 넣기 | 탭 페이지는 그 탭 담당만 수정(홈 KHS, 탭 1 JUJ(첫 화면 화주 선택은 KHS), 탭 2 YHS, 탭 3 LSY, 탭 4 KHS, 탭 5 KHS). 다른 담당은 부품을 만들어 props만 알려 줌([RULES.md 6장](RULES.md#6-탭과-부품의-경계)) |
| 화면 문구 | 한 파일에 모두 추가 | `lib/text/<영역>.ts`로 나눔 |
| `rules/shippers/*.json` | 설정 키 추가 | JUJ만 수정. 다른 담당은 필요한 키를 요청 |
| `samples/` | 가상 서류 추가 | 화주·B/L 폴더 단위로 추가, 기존 폴더 파일은 만든 사람만 수정 |
| 줄바꿈(Windows CRLF) | 파일 전체가 바뀐 것처럼 보임 | `.gitattributes`로 LF 고정, 엑셀·PDF·이미지는 binary |
| `package-lock.json` | 각자 `npm install`하면 바뀜 | PM만 커밋. 팀원은 `npm ci` |
| `.github/CODEOWNERS` | 리뷰 알림 대상 | (제안) 폴더별 담당자를 등록해 PR이 오면 담당자에게도 알림. 수락은 PM. 팀원 GitHub 아이디 확인 필요 |
| 포맷 차이 | 따옴표·들여쓰기만 다른 수정 | ruff format·prettier를 저장 시 자동 실행, 설정 파일은 PM이 1일차에 고정 |

### 4-4. 기존 도구를 보고 바꾼 것 (제안)

| 바꾼 것 | 이유 |
|---|---|
| 기능 ID마다 폴더 | 팀원 4명 동시 작업 충돌 방지, 기능별 테스트·PR 단위가 분명해짐 |
| 테스트를 각 기능 폴더 안 `tests/`에 | 공용 `tests/` 폴더에서 나던 충돌 방지. `backend/tests/e2e/`만 공용(KHS) |
| 유니패스를 `core/unipass/` | 기존 `common/unipass_client.py`처럼 공통이다. 반입 상태(A1)·승인일 조회(A2)·관세환율이 함께 쓴다 |
| `app/law_data/` 추가 | 기존 `law_data/`가 Supabase 공개 정보의 원천이고, A3 재질 코드 후보·재질 구분이 의존한다 |
| `scripts/seed/` 추가 | SCAM_DATA 적재는 PM만 실행한다(5-2) |
| `rules/*.json` 키 이름 = 기존 `CompanyRules` 필드 이름 | 이관 때 기존 도구와 연결하기 쉽다([RULES.md 11-11](RULES.md#11-11-화주별-특이-규칙)) |
| 품목사항 양식은 머리글만 다시 만든 파일 | 회사 시트 원본을 공개 저장소에 올리지 않기 위해 |

### 4-5. 3번 판단(a3_judge, LSY) 상세

3번은 기존 도구에서 가장 많은 모듈(`precise.py` `declarations.py` `overseas_maker.py` `factories.py` `spec_class.py` `material_equiv.py` `color_check.py` `spare_parts.py` `regroup.py` `rule_check.py` `item_sheet.py` `history.py` `companies/`)에 걸쳐 있다. 판단 하나하나가 따로 테스트되어야 하므로 **판단 단계마다 폴더, 규칙 하나마다 파일**로 나눈다.

**판단 순서 (한 행 기준):** 이력 조회 → 재질 → 재질 구분 → 제조사 코드 → 실적 → 색상 → 규칙 검사 → (여러 행) 신고건 나누기 → 품목사항

```
a3_judge/                                  (LSY)
├─ router.py                영역 라우터: GET /judge/{row_id}, POST /judge/declarations, POST /judge/item-sheet
├─ pipeline/                판단 순서 실행
│  ├─ judge_row.py          한 행: 아래 단계를 순서대로 부르고 Field(ai_value·evidence·flag)로 묶음. final_value 있는 칸은 건너뜀
│  ├─ judge_batch.py        여러 행(새로고침·설정 변경 시 재계산), 승인 행 제외
│  └─ evidence.py           Evidence 만들기 공통 함수 (RULES 10장 형식)
├─ history_lookup/          [A3-1] 과거 검역이력에서 고정 값 찾기           ← history.py
│  ├─ model_key.py          모델 코드 추출, 완제품/부분품 구분, 제조사 "회사명 (코드)" 나누기
│  └─ lookup.py             모델+완제품/부분품 단위 최근 행: 영문·한글 제품명, 재질, 실적번호, 제조사
├─ material/                [A3-1] 재질 판단                              ← declarations.resolve_material
│  ├─ sources/              판단 근거 4가지, 순서대로 (RULES 11-4)
│  │  ├─ from_history.py        ① 이력
│  │  ├─ from_import_decl.py    ② 이전 수입신고서 (A2 products의 service 호출)
│  │  ├─ from_test_report.py    ③ 시험성적서 검체 재질
│  │  └─ from_label_photo.py    ④ 현품사진·라벨 (마지막, 단독 확정 금지)
│  ├─ resolve.py            ①→④ 순서 적용, 후보 목록 + 근거, 근거 없으면 "확인 필요"
│  ├─ codes.py              약어 → 재질 코드명(Supabase material_aliases), 가나다 정렬, 식품 접촉 재질만
│  ├─ equiv.py              라벨 표기 ↔ 코드명 같은 재질인지 ('불소수지' = '금속제(불소수지도장)')   ← material_equiv.py
│  ├─ label_diff.py         이전 신고 재질과 라벨이 다를 때 경고 문구            ← label_diff, photo_warning
│  └─ unmodeled.py          모델 코드 없는 행(부속품만 신고 등) 영문명으로 자료 찾기  ← unmodeled.py
├─ spec_class/              [A3-1] 재질 구분 — 유리제·도자기제·법랑·옹기류만     ← spec_class.py
│  ├─ family.py             재질이 4종에 해당하는지
│  ├─ tables.py             구분표(공전 총칙 3.자) 읽기 — 기준 수치는 rules/default.json
│  └─ classify.py           깊이 2.5cm·용량·가열조리용 → 구분 값, 모자란 입력 목록
├─ factory/                 [A3-3] 해외제조업소 코드                       ← overseas_maker.py, factories.py
│  ├─ candidates.py         회사명 → 등록 공장 목록(core 식약처 API), 시설 취소·취하 상태
│  ├─ address.py            주소 정규화·유사도(addr_score). 기준 0.45, 2등과 0.1 차 → 설정값
│  ├─ choose.py             선택 순서: 회사명 → C/O 생산자 주소 → 이전 신고 코드 → 수기 (prefer_past_factory_code면 순서 바꿈)
│  └─ same_factory.py       코드가 달라도 주소가 같으면 같은 공장(코드 갱신 추정)
├─ record_pick/             [A3-2] 실적 고르기                             ← precise.py
│  ├─ eligibility.py        쓸 수 있는 실적인지: 같은 공장, 재질 모두 포함, 같은 품명 (covers, match_by)
│  ├─ spec_filter.py        재질 구분이 같은 실적만 (spec_filter)
│  ├─ rank.py               재질 가장 많이 포함 → 만료면 다음 (choose_approval). 만료 판정은 A2 records 함수 사용
│  ├─ spare_rule.py         부속품만 신고 → 본품 실적 사용(한 방향), spare_same_as_model
│  ├─ multi_record.py       신고건당 실적 여러 개(B사), 뚜껑 등 부품별 실적 분리(split_record_by_part)
│  └─ no_record.py          유효 실적 없음 → "정밀검사 필요", 진행 중 정밀검사 표시 (waiting_status)
├─ color/                   [A3-6] 색상 비교 (color_check=true 화주만)      ← color_check.py
│  ├─ families.py           색 이름 → 색 계열
│  └─ check.py              실적 성적서 검체 색 ↔ 현품 부위 색, 다르면 "추가 정밀검사 필요" 문구. 사진 추정색은 확정에 안 씀
├─ spare_parts/             부분품 처리 (A사 merge_spare_parts)             ← spare_parts.py, regroup.regroup_spare
│  ├─ collect.py            CI 부분품 줄(부품번호·품명·수량)을 B/L별로 기록
│  ├─ merge.py              본품 모델 1행으로 합치기, 수량으로 CI 줄과 짝 맞추기
│  └─ model_change.py       담당자가 부분품 신고 모델을 바꾸면 영문명·재질·실적 다시 계산
├─ rule_check/              규칙 위배 검사 — 값은 바꾸지 않고 표시만        ← rule_check.py
│  ├─ material_rule.py      공식 코드명 아님·이명·가나다 순 아님
│  ├─ record_rule.py        실적이 재질을 다 포함하지 않음·다른 품명·다른 공장·만료
│  └─ maker_rule.py         제조사 주소가 서류와 다름
├─ grouping/                [A3-4] 신고건 나누기                            ← companies.group_key, regroup.py
│  ├─ keys.py               모선(화물관리번호 앞 11자리)·제조업소·재질·색상 키 (화주 설정으로 켜고 끔)
│  ├─ split.py              반드시 조건(모선·제조업소) 위배 금지, 최대 행 수(B사 5) 끊기
│  ├─ order.py              신고건 안 행 순서, 대표품목(첫 행)
│  ├─ arrival.py            가장 최근 반입일, 반입일 들어온 묶음만 '신청 전'
│  └─ regroup.py            사람이 재질·모델을 바꾸면 해당 행만 다시 묶기 (place_added)
├─ item_sheet/              [A3-5] 품목사항 엑셀 (AI 없음)                  ← item_sheet.py
│  ├─ validate.py           한 신고건인지 검사, 아니면 거부 (check_one_declaration)
│  ├─ build.py              행 → 품목사항 칸 (수량=카톤 수, 과세가격=가격(USD), 화물관리번호 1·2·3)
│  └─ writer.py             templates/item_sheet.xlsx에 쓰기, 칸 길이 제한 검사
└─ ai_material/             [A3-7] AI 신제품 재질 후보 (P2)                ← learning.py 참고
   ├─ candidates.py         라벨·재질증명서 → 재질 코드 후보 (core/llm.py 경유)
   └─ learn.py              담당자 수정 값을 다음 판단의 예시로 (신규 모델 수정 학습)
```
각 폴더 안에 `tests/`가 있다. 규칙 파일 하나에 테스트 파일 하나를 맞춘다(예: `record_pick/tests/test_rank.py`).

**3번 우선순위**

| 순서 | 폴더 | 우선 | 이유 |
|---|---|---|---|
| 1 | `history_lookup/`, `material/sources/from_history.py`, `material/codes.py` | P0 | 이력만으로 재질 채우기(P0 연결) |
| 2 | `grouping/keys.py` `split.py` `order.py`, `item_sheet/` | P0 | 품목사항 엑셀까지 연결 |
| 3 | `pipeline/` | P0 | 단계를 한 곳에서 부르기 |
| 4 | `record_pick/` `factory/` | P1 | 시나리오 (a)(b) |
| 5 | `material/` 나머지, `spec_class/`, `spare_parts/`, `rule_check/`, `grouping/arrival.py` `regroup.py` | P1 | A사·B사 차이 시연(c) |
| 6 | `color/`, `ai_material/` | P2 | 후순위 |

**3번이 다른 영역에서 받아 쓰는 것** (그 폴더 `service.py` 공개 함수만)

| 필요한 것 | 어디서 | 담당 |
|---|---|---|
| 실적 목록, 만료 판정(승인일+5년) | `a2_registry/records/` | YHS |
| 이전 수입신고서·성적서 재질, 제품별 제조업소 | `a2_registry/products/` | YHS |
| 화주 설정 스위치 | `a4_settings/engine/` `get_rules(shipper_id)` | JUJ |
| 검역이력 행 읽기·ai_value 쓰기 | `a1_history/rows/` | KHS |
| 재질 코드·약어(Supabase), 식약처 공장 API, LLM | `core/storage/public_db.py`, `core/`, `core/llm.py` | KHS |

3번 안에서도 폴더끼리는 `service.py` 공개 함수로만 부른다. 일이 많으므로 P1 이후 `color/`, `spare_parts/`, `rule_check/` 중 일부를 다른 팀원에게 나눠 줄 수 있다(PM 결정, 소유표만 바꾸면 된다).

---

## 5장. 데이터

### 5-1. 저장 3구분

| 저장소 | 무엇을 | 누가 쓰나 | 비고 |
|---|---|---|---|
| **구글 드라이브** (실무 기준) | 화주 서류 접수 폴더·처리완료 폴더, 시험성적서·수입신고서 원본, 확정된 검역이력·실적 이력 | 프로그램(담당자 계정) | 회사 방침: 업체 서류는 외부 서버·DB 대신 드라이브 |
| **로컬 SQLite** (`data/app.db`) | 작업 중 데이터, 판독 결과, AI 결과(`ai_value`)와 확정 값(`final_value`), 캐시 | 프로그램 | 외부로 나가지 않음. git 제외 |
| **Supabase** (`declaration_list_ax`, 서울) | ① 공개 정보: 재질 코드·약어, 공전·표시기준 본문, 관세환율 → 공개 키로 읽기 ② **고객사 자료(SAMC_DATA)**: 파일 목록·추출 텍스트·JSON·엑셀 행 표(`samc_*`)와 원본 파일(비공개 Storage `samc-originals`) → **프로그램 계정으로 로그인해야** 읽기 | 읽기: 팀 전원 / 쓰기: PM(secret 키)만 | ②는 PM 결정(11/25). 팀원은 데이터를 받아 쓰기만 하고 고치지 않는다 |

### 5-2. DB 관리 권한 (PM만)
- Supabase 쓰기 키(`SUPABASE_SERVICE_ROLE_KEY` = 대시보드의 secret 키)는 PM만 갖는다. 팀원 `.env`에는 `SUPABASE_URL`과 `SUPABASE_ANON_KEY`(= publishable 키, 읽기)만 넣는다.
- 키 확인 위치: [Supabase 대시보드](https://supabase.com/dashboard/project/cqxmndycpbozjfrtlvbi) → Project Settings → API Keys. publishable 키(`sb_publishable_…`)는 팀원용, secret 키(`sb_secret_…`)는 PM만 본다.
- 모든 Supabase 테이블은 RLS를 켜고 `select` 정책만 둔다. 쓰기 정책을 만들지 않는다. 공개 정보 표는 `anon`도 읽고, `samc_*` 표와 `samc-originals` 버킷은 `authenticated`(프로그램 계정 로그인)만 읽는다.
- 테이블 추가·변경은 `supabase/migrations/`에 PM이 마이그레이션 파일로만 한다.
- SAMC_DATA 적재 순서(PM만): ① `build_local_seed.py <SAMC_DATA>` → PM PC `data/app.db` ② `build_public_seed.py` → `data/public_seed.sql` ③ `push_supabase.py` → Supabase(계정 생성, 원본 Storage, `samc_*` 표, `law_documents`). 2026-11-25 로컬 적재: 파일 283, 텍스트 268개 파일(스캔 PDF는 OCR), 시트 행 56,694, JSON 86. 재질 코드 135·약어 40도 `push_supabase.py`가 함께 올린다(2026-11-25 새 프로젝트로 옮김).
- 팀원은 `data/app.db`를 받지 않는다. Supabase에서 읽는다(`core/storage/public_db.py`).

### 5-3. Supabase 테이블
| 테이블 | 칸 | 출처 / 읽기 권한 |
|---|---|---|
| `material_codes` | name(재질 코드명), code(14자리, 예: D5000002B20000), source, as_of | 식약처 성분코드 API, 법령자료 03 |
| `material_aliases` | alias(PP·스테인리스 등), name(공식 코드명) | 기존 도구 재질 약어표 |
| `law_documents` | doc_no, title, body, source, as_of | 법령자료 00·01·02·03·04·07·09 (06·08·10·11·12는 화주 정보가 섞여 제외) |
| `fx_rates` | week_start, currency, rate_krw | 유니패스 관세환율 |
| `samc_files` | path, top, category(intake·shipping_docs·inspection_data·sheet·law·company_program), doc_kind, shipper(A기업·B기업 가명), ext, size, sha256, storage_path | SAMC_DATA / **로그인만** |
| `samc_texts` | path, part(p1·시트명·ocr_p1…), text | PDF·엑셀·docx·코드 글자, 스캔본 OCR / **로그인만** |
| `samc_json` | path, category, shipper, body(jsonb) | 검역 데이터·회사 프로그램 JSON / **로그인만** |
| `samc_sheet_rows` | workbook, sheet, row_no, cells(jsonb) | 검역 이력·품목사항·선적서류 엑셀 행 / **로그인만** |
| Storage `samc-originals` | `<sha256><확장자>` 원본 파일 | `samc_files.storage_path`로 찾음 / **로그인만** |

### 5-4. 로컬 SQLite 테이블
| 테이블 | 내용 | 담당 |
|---|---|---|
| `raw_json`, `raw_sheet_rows`, `raw_files`, `raw_text` | SCAM_DATA 원본 적재(원본 바이트·추출 텍스트·OCR) | KHS |
| `sessions` | 로그인 세션: token_hash, expires_at, created_at (계정은 1개라 users 표 없음) | KHS |
| `audit_log` | 누가 언제 무엇을 바꿨나(로그인, 칸 수정, 설정 저장, 계정 변경) | KHS |
| `documents` | 업로드 서류와 판독 결과(`ParsedDocument`) | KHS |
| `history_rows` | 검역이력 행(아래 5-5), 칸마다 ai/final/evidence | KHS(생성)·LSY(재질·실적 칸) |
| `mismatches` | 서류 대조 결과 | KHS |
| `declarations` | 신고건(묶음) | LSY |
| `records` | 정밀검사 실적 | YHS |
| `products` | 제품별 재질·해외제조업소(수입신고서·성적서 등록) | YHS |
| `alerts_sent` | 만료 알림 발송 기록(종류 kind=record·factory_code, 대상·단계별 1회) | YHS |
| `factories` | 해외제조업소 코드(code, name, address, registered_on, expires_on, status, source) — A2-5 | YHS |
| `shipper_settings` | 화주 설정 사본(원본은 `rules/*.json`) | JUJ |

### 5-5. 핵심 데이터 칸 정의
`backend/app/core/schema/`가 기준 코드다(PM만 수정). 아래는 설계안이다.

**칸 공통 형태 (Field)**
```python
class Evidence(BaseModel):
    source: Literal["CI", "PL", "BL", "CO", "INTAKE_LIST", "IMPORT_DECL", "TEST_REPORT", "HISTORY",
                    "PHOTO", "LABEL", "UNIPASS", "FX", "RULE", "MANUAL"]
    ref: str            # 문서 id, 이력 행 id, 규칙 키 등
    note: str = ""      # 사람이 읽을 근거 한 줄

class Field(BaseModel, Generic[T]):
    ai_value: T | None = None
    final_value: T | None = None          # 담당자 확정 값. 재실행이 덮어쓰지 않음
    evidence: list[Evidence] = []
    flag: Literal["ok", "mismatch", "edited", "need_input", "need_check"] = "ok"
    memo: str = ""                        # 지우면 '확인함' (RULES 11-9)
```

**서류 (ParsedDocument)** — A0 출력
| 칸 | 설명 |
|---|---|
| doc_id, shipper_id, folder_id | 폴더 1개 = 선적서류 1건 |
| doc_type | CI · PL · BL · CO(원산지증명서) · INTAKE_LIST(입고리스트) · IMPORT_DECL · TEST_REPORT · PHOTO · LABEL |
| bl_no, invoice_no, doc_date, vessel | |
| manufacturer_name, manufacturer_address | 원산지증명서 생산자 우선(RULES 11-7) |
| currency, total_amount, total_cartons, total_gross_kg | 서류 대조용 합계 |
| lines[] | model, description, qty_per_carton(입수), cartons, net_kg, amount, is_part(부분품), color |
| parser, warnings | excel / pdf / llm |

**검역이력 행 (HistoryRow)** — 기존 검역이력 시트(A기업 탭) 26칸 기준. 열 이름은 바꾸지 않는다.
| # | 열 이름(시트 그대로) | 채우는 방식 | 담당 |
|---|---|---|---|
| 1 | B/L Number | 서류 판독 | KHS |
| 2 | 반입지 코드 | 유니패스(최종 반입지 장치장 코드) | KHS |
| 3 | 반입일 | 유니패스. 한 신고건에 여러 B/L이면 가장 최근 날짜 | KHS |
| 4 | 입항일 | 유니패스 | KHS |
| 5 | 선적일 | 서류 판독(B/L) | KHS |
| 6 | 모선명 | 서류 판독 → 유니패스 기준 | KHS |
| 7 | 도착항 코드 | 유니패스 | KHS |
| 8 | 선적항 코드 | 유니패스 | KHS |
| 9 | 제조사 | `회사명 (업소코드)`, 주소 매칭 | LSY |
| 10 | 화물관리번호 | 유니패스 | KHS |
| 11 | 한글 제품명(모델넘버) | 이력·화주 규칙(A사: 모델명 포함) | KHS |
| 12 | 입수 | 서류 판독 | KHS |
| 13 | 카톤 수 | 서류 판독 | KHS |
| 14 | 순중량 | 서류 판독 | KHS |
| 15 | 가격(USD) | 계산식: 가격(수출국) × CI 통화 환율 ÷ USD 환율 (직접 입력 금지) | KHS |
| 16 | USD 환율 | 관세환율, 숨김 | KHS |
| 17 | CI 통화 | 서류 판독, 숨김 | KHS |
| 18 | 가격(수출국) | CI 금액(Amount) 그대로 | KHS |
| 19 | CI 통화 환율 | 관세환율, 숨김 | KHS |
| 20 | 재질 (재질 코드명으로 작성, 가나다 순으로 기재) | 재질 판단 순서 | LSY |
| 21 | 실적접수번호 (승인일) | 실적 선택, 값 형식 `202300233982 (2023.04.25)` | LSY |
| 22 | 영문 제품명 | 서류 판독 | KHS |
| 23 | 재질 구분 (깊이·용량·용도) | 유리제·도자기제·법랑·옹기류만 | LSY |
| 24 | 검역 신고일자 | 담당자 입력 / 유니패스 | KHS |
| 25 | 승인번호 | 유니패스. 있으면 그 행은 수정 금지 | KHS |
| 26 | 비고 | 진행 상황·경고(⚠️ 태그별 한 줄) | KHS |

B사 탭은 `색상` 열이 재질 다음에 있다. 행에는 추가로 `row_id, shipper_id, declaration_id, is_part, parent_row_id, status(자료 추가 필요 / 확인 필요 / 신청 전 / 승인), source_doc_ids` 를 둔다.

**신고건 (Declaration)** — A3 출력. 빈 행 1개 = 신고건 경계(기존 시트)를 데이터로 옮긴 것.
| 칸 | 설명 |
|---|---|
| declaration_id, shipper_id | |
| key | 모선(화물관리번호 앞 11자리), 제조업소 코드, 재질, (색상) |
| row_ids[] | 순서 유지(정렬 기준은 화주 설정) |
| record_nos[] | 사용 실적접수번호. 기본 1개, 화주 설정에 따라 여러 개 |
| arrival_date | 묶인 B/L 중 가장 최근 반입일 |
| warnings[] | 규칙 위배(다른 모선·제조사 섞임 등) |

**실적 (Record)** — A2 소유
| 칸 | 설명 |
|---|---|
| record_no | 실적접수번호 |
| factory_code, factory_name, factory_address | 해외제조업소 |
| materials[] | 실적 재질(그 실적으로 승인된 행의 재질만) |
| spec_class | 재질 구분(유리제 등) |
| sample_parts[] | 시험성적서 검체: 재질·부품·색상 |
| applied_on, approved_on, expires_on | 만료일 = 승인일 + 5년(설정값) |
| products[] | 이 실적으로 신고한 모델(정밀/서류 구분) |
| status | 유효 · 만료 임박 · 만료(취소선 표시) |

**화주 설정 (ShipperSettings)** — A4 소유. 형식은 [RULES.md 11-11](RULES.md#11-11-화주별-특이-규칙).

---

## 6장. API

기본 주소 `http://127.0.0.1:8000/api`. 담당별 prefix를 쓰고 다른 담당의 prefix에 엔드포인트를 만들지 않는다. 오류 응답은 `{"error": {"code": "...", "message": "..."}}`.

**로그인:** `/core/auth/login`과 `/core/health`를 뺀 모든 API는 `Authorization: Bearer <토큰>`이 있어야 한다. 확인은 `main.py`에서 `core/auth`의 의존성(`require_login`)을 라우터 등록 시 한 번에 건다. 기능 폴더에서 따로 로그인 확인 코드를 쓰지 않는다. 토큰이 없거나 만료면 401 → 화면은 `/login`으로 보낸다.

| 메서드·경로 | 담당 | 설명 | 우선 |
|---|---|---|---|
| `POST /core/auth/login` (username, password) | KHS | 로그인 → Supabase Auth로 확인(`<username>@declaration.local`) → 세션 토큰. 5회 틀리면 10분 잠금 | P0 |
| `POST /core/auth/logout` | KHS | 세션 삭제 | P0 |
| `GET /core/auth/me` | KHS | 로그인 상태 확인 | P0 |
| `GET /core/health` | KHS | 상태, LLM·유니패스 모드 (로그인 없이 허용) | P0 |
| `GET /core/shippers` | KHS | 화주 목록(가명) | P0 |
| `POST /reader/upload` (multipart, shipper_id) | KHS | 서류 올리기 → 판독 → 행 생성까지. 응답: 생성·갱신 row_id | P0 |
| `GET /reader/documents/{doc_id}` · `/file` | KHS | 판독 결과 / 원본 보기 | P1 |
| `GET /history?shipper_id=&status=` | KHS | 검역이력 표 | P0 |
| `PATCH /history/{row_id}` | KHS | 담당자 수정(final_value). 재질·제조사가 바뀌면 A3 재계산 | P0 |
| `POST /history/refresh?shipper_id=` | KHS | 새로고침: 대조·유니패스·재계산(확정 값 유지) | P1 |
| `GET /history/{row_id}/review` | KHS | 검수 패널 데이터 | P1 |
| `POST /history/{row_id}/confirm` | KHS | 확인함 | P1 |
| `GET /history/badges?shipper_id=` | KHS | 확인 필요 n, 진행 중 n | P0 |
| `POST /registry/upload` (multipart) | YHS | 수입신고서·성적서 → 등록 후보 | P1 |
| `GET /registry/records?shipper_id=&maker=&model=` | YHS | 실적 탭 | P1 |
| `PATCH /registry/records/{record_no}` | YHS | 실적 수정 | P1 |
| `GET /registry/alerts?within_days=` | YHS | 만료 임박 | P1 |
| `POST /registry/alerts/send` | YHS | 만료 알림 메일 발송(수동·예약). 실적·해외제조업소 코드 둘 다 | P1 |
| `GET /registry/factories?within_days=` | YHS | 해외제조업소 코드 목록·만료일·상태(A2-5) | P1 |
| `PATCH /registry/factories/{code}` | YHS | 등록(갱신)일 수정 → 만료일 다시 계산 | P1 |
| `GET /judge/{row_id}` | LSY | 재질·실적·제조사 판단 근거와 후보 | P1 |
| `POST /judge/declarations?shipper_id=` | LSY | 신고건 나누기 계산 | P0 |
| `POST /judge/item-sheet` (body: row_ids) | LSY | 한 신고건 확인 → 품목사항 엑셀 생성 | P0 |
| `GET /judge/item-sheet/{file_id}` | LSY | 엑셀 다운로드 | P0 |
| `GET /settings/rules` | JUJ | 규칙 목록(공통/선택, 설명) | P1 |
| `GET /settings/shippers/{id}` · `PUT` · `POST /settings/shippers` | JUJ | 화주 설정 조회·저장·추가 | P1 |
| `POST /settings/shippers/{id}/dry-run` | JUJ | 시험 실행(저장 없이 결과 미리보기) | P1 |
| `DELETE /settings/shippers/{id}` | JUJ (HS 요청 11/25, KHS 작성 — JUJ 확인 필요) | 화주 삭제. 기본 A·B는 409, 설정 파일은 `DATA_DIR/deleted_shippers/`로 옮겨 백업 | P1 |
| `GET /core/connections` · `POST /core/connections/check` · `PUT /core/ai-choice` | KHS | 탭 5 연결 설정 화면용: 연결 상태 표, [연결 검사](실제 접속, AI는 모델 목록만 받아 토큰 안 씀), 사용할 AI·모델 고르기(`data/ai_choice.json`, .env보다 우선) — HS 요청 11/25 [신규] | P1 |

화면별 호출은 [DESIGN.md](DESIGN.md)에 있다.

---

## 7장. AI 호출 규칙

1. **한 곳에서만:** `core/llm.py`의 `call_structured(prompt_name, version, inputs, schema)`만 쓴다. 다른 파일에서 SDK를 import하지 않는다.
2. **화주명 가리기:** 보내기 전에 `core/masking.py`가 화주명·수입자명·주소의 화주 부분을 `[화주]`로 바꾼다. 돌려받은 값은 다시 채우지 않는다(화주명은 결과에 필요 없다).
3. **구조화 출력:** 응답은 JSON으로 받고 Pydantic 스키마로 검증한다. 검증 실패·형식 오류면 **1회만** 재시도하고, 또 실패하면 그 칸을 "확인 필요"로 둔다. 기존 도구 기록: Claude의 형식 강제는 복잡한 판독 스키마를 거절했으므로 스키마를 지시문에 붙이고 Pydantic으로 검증했다.
4. **프롬프트 버전:** 원문은 `backend/prompts/<영역>/<이름>.v<N>.md`. 고칠 때는 새 버전 파일을 만들고 코드에서 버전을 올린다. 예: `read_shipping_docs.v1.md`, `material_candidates.v1.md`, `factory_match.v1.md`.
5. **AI를 쓰지 않는 일:** 품목사항 생성, 신고건 나누기, 실적 만료 계산, 실적 선택(규칙), 가격(USD) 계산, 서류 대조(숫자 비교).
6. **AI를 쓰는 일:** 서류 판독(표가 안 읽히는 PDF·스캔), 재질 코드 후보, 제조사 주소 표기 차이 판단(규칙 점수로 애매할 때만), 신제품 재질(P2).
7. **꺼도 동작:** `LLM_ENABLED=false`면 AI 단계는 건너뛰고 "확인 필요"를 남긴다.
8. **기록:** 호출마다 기능·프롬프트 버전·토큰·추정 비용을 로컬 `logs/ai_usage.jsonl`에 남긴다(기존 도구와 같은 방식). 서류 원문은 로그에 남기지 않는다.
9. **사진만으로 재질을 확정하지 않는다.** 기존 도구 시험에서 실패했다(미팅 11/24).

---

## 8장. 외부 연동

| 연동 | 용도 | 담당 | 규칙 |
|---|---|---|---|
| 구글 드라이브 | 서류 접수 폴더 → 처리완료 이동, 업로드 사본 저장 | KHS(접수·이동), YHS(성적서) | 공유본 폴더 ID만 `.env`에. 운영 폴더 ID 금지. 지우기 대신 휴지통 |
| Gmail | 실적·해외제조업소 코드 만료 알림(3개월·1개월 전) | YHS | 같은 대상·같은 단계는 1번만. 발신 계정은 열린 질문 |
| 유니패스 | 반입 상태·반입일·반입지·입항일, 검사검역내역(승인일), 관세환율 | KHS | `UNIPASS_MODE=mock`이면 `samples/unipass/*.json` 반환. **신청서 작성·전송 금지** |
| 식약처·공공데이터포털 | 재질 코드, 해외제조업소 | KHS(law_data) | 결과는 Supabase(공개)·로컬 캐시 |
| 식품안전나라 | 기구 및 용기·포장 공전 기준 | KHS | |
| 법제처 OPEN API | 공전 고시 원문, 개정 감시 | KHS | **등록한 공인 IP에서만 동작.** PC마다 등록 |

---

## 9장. 환경 변수

이름만 적는다. 값과 설명은 `.env.example`.
```
APP_ENV API_HOST API_PORT CORS_ORIGINS DATA_DIR LOCAL_DB_PATH SOFFICE_PATH
AUTH_ENABLED AUTH_SECRET_KEY AUTH_SESSION_HOURS ADMIN_USERNAME ADMIN_PASSWORD ADMIN_DISPLAY_NAME
LLM_ENABLED AI_PROVIDER ANTHROPIC_API_KEY CLAUDE_MODEL OPENAI_API_KEY OPENAI_MODEL MASK_SHIPPER_NAMES
GOOGLE_CREDENTIALS_FILE GOOGLE_TOKEN_FILE DRIVE_INBOX_FOLDER_ID DRIVE_LAW_FOLDER_ID STUDENT_DATA_FOLDER_ID
SPREADSHEET_ID ITEM_SPREADSHEET_ID GMAIL_SENDER ALERT_EMAIL_TO ALERT_DAYS_BEFORE FACTORY_CODE_VALID_YEARS
UNIPASS_MODE UNIPASS_CARGO_API_KEY UNIPASS_CUSTOMS_CHECK_API_KEY UNIPASS_INSPECTION_API_KEY
UNIPASS_SHED_API_KEY UNIPASS_FXRT_API_KEY UNIPASS_REQ_STATUS_API_KEY
LAW_API_OC DATA_GO_KR_SERVICE_KEY MFDS_MATERIAL_CODE_API_KEY MFDS_IMPORT_RCPT_ENTP_API_KEY
MFDS_OVERSEAS_MAKER_API_KEY FOODSAFETY_API_KEY
SUPABASE_URL SUPABASE_ANON_KEY SUPABASE_SERVICE_ROLE_KEY
frontend: NEXT_PUBLIC_API_BASE
```

---

## 10장. 개발 순서

| 시기 | 목표 | 완료 기준 |
|---|---|---|
| 1주차 화(11/24) | 문서 4종, `core/schema/` 합의, 저장소 골격(`main.py` 라우터, `layout.tsx` 메뉴), **로그인(C-4)** | 팀 리뷰, 어드민 계정으로 로그인 → 홈 진입 |
| 1주차 수 | **P0 연결:** 가상 B/L 1건 → 판독 → 검역이력 행 → 신고건 → 품목사항 엑셀 | 홈에서 표가 보이고 엑셀이 내려받아진다 |
| 1주차 목·금 | P1 착수: 서류 대조·검수 패널, 실적 등록·실적 탭, 실적 선택, 화주 설정 화면 | 시나리오별 API 동작 |
| 1주차 금~ | SAMC 줌 피드백 준비(다음 주 월·화) | 시연 시나리오 3종 대본 |
| 2주차 | 고도화: 판독 정확도, 실적 선택 일치율, 처리 시간 측정, 가상 화주 2곳 시연, 만료 메일 | 성과지표 표 |
| 마지막 | exe 변환, 이관 문서(`docs/handover/`) | exe로 시나리오 3종 재현 |

주기 작업(기존 도구의 5분·1분·19:30 작업)은 우리 프로그램에서 "새로고침" 버튼과 프로그램 시작 시 1회 실행으로 대신한다(제안). 상시 자동 실행 여부는 열린 질문이다.

---

## 11장. 열린 질문

미팅 정리의 [확인 필요]
- [ ] 1. 화면·문서 용어: "검역" vs 법령상 "수입신고 검사(서류검사·정밀검사·무작위표본검사)"
- [ ] 2. 화물관리번호 앞 11자리 = 동일 모선 판정이 맞는지(선사가 다르면 달라질 수 있음)
- [ ] 3. 색이 다른 제품을 한 신고건에 묶을 때 실적번호 여러 개 입력 조건(B사만? 공통?)
- [ ] 4. 재질 포함 규칙의 근거 기준과 예외(로직은 기존 코드로 확인, 근거 조항 미확인)
- [ ] 5. 신청서 필수 칸 범위(공통사항·품목사항·한글표시사항·재질·첨부)
- [ ] 6. HS 코드 판별 불필요의 범위(HS 개정 주의)
- [ ] 7. 유리제·법랑·옹기류·도자기제 세분 기준(공전 총칙 3.자·구분표, 수치 최신본 확인 필요)
- [ ] 8. A사 예외(과거 제조업소 코드 유지, 부분품 본품 한 모델로 몰기, 단가 몰기)의 허용 근거
- [ ] 9. (이 저장소는 기준 개정 감시만 해당) 법령 API가 식약처 주간 공문과 일치하는지

설계 결정
- [ ] 한 행 단위: 제품 1행(현재 검역시트) vs 신고건 1행(참고 통관 프로그램) — [DESIGN.md 9장](DESIGN.md#9-한-행-단위-비교)
- [ ] 화주 규칙: 사용자가 직접 추가 vs 미리 만든 규칙에서 고르기(현재 설계: 미리 만든 규칙 + 값 입력)
- [ ] 검역이력 원본 위치: 구글 시트를 계속 쓰는지(기존 도구 연계), 우리 화면 + 드라이브 파일로 바꾸는지
- [ ] 유니패스 API 계정 제공 시점(그 전에는 mock)
- [ ] 해외제조업소 코드 실시간 반영 여부(기존 도구 기록: API 반영 1~2개월 지연)
- [ ] 고객사 자료를 Supabase(로그인 읽기 전용)에 두는 방식에 대한 회사 동의
- [ ] exe 변환 방식(Tauri / Electron + PyInstaller / 브라우저 실행)
- [ ] 성과지표(판독 정확도, 실적 선택 일치율, 처리 시간)와 최종 검수 담당자
- [ ] 만료 알림 메일 발신 계정(회사 구글 비즈니스 계정 사용 가능 여부)과 수신자
- [ ] 주기 작업(상시 자동 실행)을 둘지, 새로고침으로 대신할지
- [ ] 참고 통관 프로그램 이름·화면 캡처
- [ ] 한 폴더에 B/L이 여러 개일 때 처리 방식(기존 도구도 미정)
- [ ] 시험성적서 원본 보관 기간(기존 도구: 실적 만료 + 2개월 뒤 휴지통)
- [ ] 신고건 정렬 기준(품목군 등)과 재질 판단 근거 순서를 화주마다 어디까지 설정으로 열지
- [ ] B사 한글 제품명 규칙, `same_record_same_spec` A사·B사 값
- [ ] 폴더별 CODEOWNERS에 넣을 팀원 GitHub 아이디(YHS·LSY·JUJ)

자료
- [ ] 선적서류 샘플(CI·PL·B/L·원산지증명서): 공유본에 없음 → 가상 서류 제작 또는 SAMC 요청
- [ ] B사 선적서류 표본(기존 도구도 B사 자동 판독 꺼짐)
- [ ] Python 3.12와 기존 도구 패키지(3.15 고정) 호환
- [ ] 판독 AI 비교: 기존 Gemini 판독 vs Claude·GPT

---

## 12장. 용어 빠른 참조

| 용어 | 뜻 |
|---|---|
| 화주 | 수입하는 고객사. 문서에서는 A사(가전)·B사(주방용품) |
| 검역이력 (시트) | 신고할 제품을 한 행씩 적는 표. 열 순서 = 신청서 입력 순서 |
| 신고건 | 신청서 1장. 검역이력에서 빈 행 1개가 경계 |
| 품목사항 | 신청서의 품목 표. 유니패스 지정 엑셀 양식으로 업로드 |
| 정밀검사(정밀검역) | 검사 이력이 없는 제조업소·재질을 검체로 검사 |
| 서류검사(서류검역) | 유효한 실적이 있어 실적번호로 서류만 처리 |
| 무작위표본검사 | 실적이 있어도 식약처가 임의 지정. 통과하면 새 실적 |
| 실적 / 실적접수번호 | 이 제조업소의 이 재질이 정밀검사를 통과한 증명. 승인일 + 5년 |
| 해외제조업소 코드 | 식약처 등록 공장 코드. 회사명이 같아도 주소가 다르면 다른 코드 |
| 재질 코드 | 식약처 재질 코드(14자리)와 재질 코드명(예: 금속제(불소수지도장)) |
| 재질 구분 | 유리제·도자기제·법랑·옹기류의 깊이·용량·용도 구분 |
| 모선 | 화물을 실은 배. 화물관리번호 앞 11자리로 판단(확인 필요 2) |
| 반입지 / 반입일 | 입항적재화물목록에 적힌 최종 장소 / 그곳에 들어온 날 |
| 부분품 | 본품(밥솥)의 부품(내솥 등). A사는 본품 한 모델로 합쳐 신고 |
| 내색 / 외색 | 그릇 안쪽 / 바깥쪽 색. B사는 신고건을 나눌 때 씀 |
| 입수 | 카톤 1개에 든 수량 |
| 시험성적서 / 검사성적서 | 정밀검사 결과 문서(수입식품정보마루에서 내려받음) |
| 수입신고서 | 이전에 신고한 신청서. 재질 판단 근거 |
| 공전 | 기구 및 용기·포장의 기준 및 규격(식약처 고시) |
| ai_value / final_value | 프로그램 결과 / 담당자 확정 값 |

---

## 13장. 작업 요청 프롬프트 (복사해서 사용)

AI 코딩 도구에 붙여 넣기 전에 `< >` 부분을 채운다.

**공통 머리말 (모든 요청 앞에)**
```
이 저장소의 AGENTS.md 0장과 RULES.md를 먼저 읽고 지켜라.
나는 <이니셜>이고 담당 폴더는 <폴더>다. 그 밖의 파일은 고치지 말고, 고쳐야 하면 이유만 보고해라.
한 번에 아래 작업 하나만 하라. 끝나면 AGENTS.md 0-8 완료 기준을 확인하고 바꾼 파일과 확인 방법을 요약해라.
```

**KHS — 서류 판독 (A0-1, P0)**
```
backend/app/a0_reader/ 에 선적서류 판독을 만들어라.
- 입력: samples/A사/<B/L 폴더>의 CI·PL·B/L(엑셀·PDF). 출력: core/schema/document.py의 ParsedDocument. 작업 폴더: backend/app/a0_reader/extract/
- 엑셀은 openpyxl, 글자 PDF는 pymupdf로 먼저 읽고, 표가 안 읽히면 core/llm.py의 call_structured("read_shipping_docs", 1, ...)를 부른다.
- 프롬프트는 backend/prompts/a0_reader/read_shipping_docs.v1.md 에 둔다. 화주명은 core/masking.py로 가린다.
- backend/app/a0_reader/extract/tests/test_extract.py 에 가상 서류 1건의 필수 칸(B/L, 모선, 제조사, 모델, 입수, 카톤, 순중량, 금액) 테스트를 넣어라.
```

**KHS — 검수 패널 (A1-4, P1)**
```
frontend/components/review/ReviewPanel/ 에 서류 검수 패널을 만들어라. DESIGN.md 4장 와이어프레임을 따른다.
- props: rowId: string, onConfirmed: () => void
- 데이터: lib/api/history.ts의 getReview(rowId), confirmRow(rowId)만 쓴다.
- 색만으로 구분하지 말고 글자(불일치/수정)를 함께 보여라. 빈·불러오는 중·오류 상태를 모두 그려라.
```

**KHS — 탭 4 검역 리스트 (H-1, P0)**
```
frontend/app/history/page.tsx 에 검역이력 표를 만들어라. DESIGN.md 3장을 따른다.
- 데이터는 lib/api/history.ts(getHistory, getBadges)만 쓴다. 홈에서 데이터를 만들거나 계산하지 마라.
- 행을 고르면 아래에 components/review/ReviewPanel 을, "품목사항 만들기"는 components/judge/ItemSheetButton 을 불러 쓴다(아직 없으면 자리표시 컴포넌트).
- 버튼은 서류 올리기·품목사항 만들기·새로고침·설정 네 개만 둔다.
```

**YHS — 실적 등록·만료 알림 (A2-1, A2-3, P1)**
```
backend/app/a2_registry/ 에 수입신고서·검사성적서 등록과 만료 알림을 만들어라.
- 1단계: samples/registry/의 판독값 JSON(기존 도구 수입신고서.json 형식)을 Record·Product로 등록하는 API(POST /registry/upload).
- 2단계: notify.py — 만료일(승인일 + 설정값 5년) 기준 ALERT_DAYS_BEFORE(90,30)일 전 실적을 찾아 Gmail로 보낸다. 같은 실적·같은 단계는 alerts_sent 에 기록하고 한 번만 보낸다.
- 만료 실적은 지우지 말고 status=만료로 남긴다. 법령 수치는 주석에 근거와 "최신본 확인 필요"를 적어라.
```

**LSY — 신고건 나누기 + 품목사항 (A3-4, A3-5, P0)**
```
backend/app/a3_judge/ 에 신고건 나누기와 품목사항 엑셀 생성을 만들어라. AI는 쓰지 않는다.
- 신고건 키: 동일 모선(화물관리번호 앞 11자리) + 동일 제조업소 코드 + 동일 재질. 화주 설정 group_by_color, max_rows_per_declaration 을 따른다(RULES.md 11-6).
- 품목사항: 체크한 행이 한 신고건이 아니면 만들지 말고 이유를 B/L·모델로 돌려줘라(기존 item_sheet.check_one_declaration).
- 양식: backend/templates/item_sheet.xlsx 머리글 15칸. 수량 = 카톤 수, 과세가격 = 가격(USD), 첫 행 대표품목 Y.
- backend/app/a3_judge/grouping/tests/test_grouping.py 에 A사·B사 가상 행으로 묶음이 달라지는 테스트를 넣어라.
```

**LSY — 재질·실적 선택 (A3-1, A3-2, P1)**
```
backend/app/a3_judge/ 에 재질 판단과 실적 선택을 만들어라. RULES.md 11-4, 11-5, 11-8을 그대로 구현한다.
- 재질 순서: 이력 → 이전 수입신고서 → 시험성적서 → 현품사진·라벨. 각 단계 결과에 evidence를 남겨라.
- 실적: 같은 공장, 모델 재질을 모두 포함하는 유효 실적 중 재질을 가장 많이 포함한 것(같으면 최신). 없으면 비고 "⚠️ 실적: 정밀검사 대상".
- 기존 도구 precise.choose_approval 의 동작과 같은지 테스트로 확인해라.
```

**JUJ — 화주 설정 (A4-1, A4-2, P1)**
```
backend/app/a4_settings/ 와 frontend/app/settings/ 에 화주 설정을 만들어라. DESIGN.md 7장, RULES.md 11-11을 따른다.
- 규칙 목록과 설명은 backend/rules/default.json 한 곳에서 읽는다. 화면 문구를 코드에 따로 쓰지 마라.
- 저장 전 Pydantic으로 검증하고, 모르는 키는 거절한다. 새 화주 = default.json 복사 + 이름.
- "시험 실행"은 POST /settings/shippers/{id}/dry-run 으로, 저장하지 않고 A1 행 합치기·A3 신고건 결과를 돌려준다.
- 가상화주A·B 설정 파일을 만들어 결과가 달라지는 테스트를 넣어라.
```

**막혔을 때**
```
지금 <무엇>을 하다가 막혔다. 고치지 말고 먼저 원인 후보 3개와 각각 확인하는 방법을 말해라.
내가 고른 방법으로만 확인하고, 담당 폴더 밖을 고쳐야 하면 고치지 말고 PM에게 보낼 요청 문장을 써라.
```

**PR 올리기 전 점검**
```
내 브랜치의 변경을 RULES.md 3장 PR 템플릿으로 정리해라. 제안서 항목 번호와 [재사용]/[개선]/[신규]를 채우고,
AI가 정한 설계 결정을 따로 적어라. 화주 실명·키·실제 서류가 들어 있지 않은지 확인해라.
```
