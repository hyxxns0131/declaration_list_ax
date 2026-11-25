"""실적·해외제조업소 코드 만료 알림: 3개월 전·1개월 전 이메일, 대상·단계별 1번만. 담당: YHS [개선] A2-3·A2-5

해외제조업소 코드(A2-5, RULES 11-8-1)도 같은 메일·같은 발송 기록(alerts_sent)을 쓴다.
기록 키: 실적은 실적번호, 업소코드는 "factory_code:<코드>" — 같은 코드·같은 단계 1회.

제안서와 다름: 미팅 11/24 합의(기존 도구는 6개월·3개월 전 시트 표시). 단계는 설정값 ALERT_DAYS_BEFORE(90,30).
만료 실적은 지우지 않는다. 메일 계정이 없으면 보내지 않고 이유를 돌려준다(DESIGN 6장).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PField

from app.a2_registry.factory_codes import service as factory_codes
from app.a2_registry.records import service as records
from app.core.config import get_settings
from app.core.schema.record import Record
from app.core.storage import gmail
from app.core.storage import work_db_more as store

FACTORY_KEY = "factory_code:"


class AlertItem(BaseModel):
    kind: Literal["record", "factory_code"] = "record"
    record_no: str  # 실적번호. kind=factory_code면 업소코드
    factory: str
    materials: list[str]
    expires_on: str
    days_left: int
    stage: int  # 90 · 30
    models: list[str] = PField(default_factory=list)
    alternative: str = ""  # 대체 실적 번호(같은 공장·재질 포함·더 늦게 만료)
    sent: bool = False

    @property
    def sent_key(self) -> str:
        return self.record_no if self.kind == "record" else f"{FACTORY_KEY}{self.record_no}"


def stage_for(days_left: int, stages: list[int]) -> int | None:
    """남은 날 → 알림 단계(가장 작은, 남은 날 이상인 단계). 이미 만료(음수)면 None. 순수 함수."""
    if days_left < 0:
        return None
    hit = [s for s in sorted(stages) if days_left <= s]
    return hit[0] if hit else None


def _alternative(rec: Record, pool: list[Record]) -> str:
    for other in pool:
        if other.record_no == rec.record_no or other.status == "만료":
            continue
        if other.factory_code != rec.factory_code:
            continue
        if not set(rec.materials) <= set(other.materials):
            continue
        if (other.expires_on or "") > (rec.expires_on or ""):
            return other.record_no
    return ""


def expiring(
    shipper_id: str | None, within_days: int | None = None, today: date | None = None
) -> list[AlertItem]:
    today = today or date.today()
    stages = get_settings().alert_days
    limit = within_days if within_days is not None else (max(stages) if stages else 90)
    pool = records.list_records(shipper_id, today=today)
    out: list[AlertItem] = []
    for rec in pool:
        exp = records.to_date(rec.expires_on)
        if not exp:
            continue
        days = (exp - today).days
        if days < 0 or days > limit:
            continue
        stage = stage_for(days, stages) or limit
        out.append(
            AlertItem(
                record_no=rec.record_no,
                factory=f"{rec.factory_name} ({rec.factory_code})".strip(),
                materials=rec.materials,
                expires_on=rec.expires_on or "",
                days_left=days,
                stage=stage,
                models=rec.products,
                alternative=_alternative(rec, pool),
                sent=store.alert_sent(rec.record_no, stage),
            )
        )
    out.extend(_factory_items(limit, stages, today))
    return sorted(out, key=lambda a: a.days_left)


def _factory_items(limit: int, stages: list[int], today: date) -> list[AlertItem]:
    """해외제조업소 코드 만료 임박(A2-5). 등록일 모르는 코드(확인 필요)는 알림에 넣지 않는다."""
    out: list[AlertItem] = []
    for f in factory_codes.list_factories(within_days=limit, today=today):
        days = f.days_left or 0
        stage = stage_for(days, stages) or limit
        out.append(
            AlertItem(
                kind="factory_code",
                record_no=f.code,
                factory=f"{f.name} ({f.code})".strip(),
                materials=[],
                expires_on=f.expires_on or "",
                days_left=days,
                stage=stage,
                sent=store.alert_sent(f"{FACTORY_KEY}{f.code}", stage),
            )
        )
    return out


def summary(items: list[AlertItem]) -> dict[int, int]:
    out: dict[int, int] = {}
    for a in items:
        out[a.stage] = out.get(a.stage, 0) + 1
    return out


def mail_text(items: list[AlertItem], shipper_label: str) -> tuple[str, str]:
    """(제목, 본문) — DESIGN 6장 미리보기 형식."""
    counts = summary(items)
    parts = [f"{_stage_label(s)} 안 {n}건" for s, n in sorted(counts.items())]
    subject = f"[실적·업소코드 만료 예정] {' · '.join(parts)} ({shipper_label})"
    lines = []
    for a in items:
        if a.kind == "factory_code":
            lines.append(
                f"- [해외제조업소 코드] {a.factory} · 만료 {a.expires_on.replace('-', '.')}"
                f" (D-{a.days_left}) → 갱신 등록 필요"
            )
            continue
        lines.append(
            f"- {a.record_no} · {a.factory} · {', '.join(a.materials)} · 만료 "
            f"{a.expires_on.replace('-', '.')} (D-{a.days_left})"
        )
        alt = (
            f"대체 실적 {a.alternative}" if a.alternative else "대체 실적 없음, 정밀검사 준비 필요"
        )
        lines.append(f"  이 실적을 쓰는 모델: {', '.join(a.models) or '-'} → {alt}")
    return subject, "\n".join(lines)


def _stage_label(days: int) -> str:
    return f"{days // 30}개월" if days % 30 == 0 else f"{days}일"


def send(shipper_id: str | None, shipper_label: str, today: date | None = None) -> dict:
    """아직 안 보낸 단계만 모아 1통. 보낸 뒤 alerts_sent에 기록."""
    ok, why = gmail.configured()
    pending = [a for a in expiring(shipper_id, today=today) if not a.sent]
    if not pending:
        return {"sent": 0, "skipped": 0, "reason": "보낼 알림이 없습니다(이미 보낸 단계는 건너뜀)."}
    if not ok:
        return {"sent": 0, "skipped": len(pending), "reason": f"메일 계정을 설정하세요 ({why})"}
    subject, body = mail_text(pending, shipper_label)
    sent, err = gmail.send(subject, body)
    if not sent:
        return {"sent": 0, "skipped": len(pending), "reason": err}
    to = ", ".join(gmail.recipients())
    for a in pending:
        store.mark_alert_sent(a.sent_key, a.stage, to)
    return {"sent": len(pending), "skipped": 0, "reason": ""}
