import html
import json
import re
from typing import List, cast
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..api.auth import normalize_user_role
from ..core.db import get_db
from ..crud.lead import (
    book_lead,
    convert_lead,
    create_lead,
    get_lead,
    get_leads,
    list_lead_activities,
    qualify_lead,
    transition_lead_status,
    upsert_missed_call_lead,
)
from ..crud.reminder import create_lead_booking_reminder, create_lead_followup_reminder
from ..models.core import Lead, Organization, User
from ..schemas.lead import (
    DemoCallIntake,
    DemoCallRequest,
    IntentIntake,
    LeadBookInput,
    LeadBookOut,
    LeadActivityOut,
    LeadConvertOut,
    LeadIntake,
    LeadOut,
    LeadQualificationInput,
    LeadQualificationOut,
    LeadStatusUpdate,
    MissedCallIntake,
    MissedCallRecoveryOut,
    PublicAttributionIn,
    RetellEventIn,
    RetellInboundCallIn,
    SupportChatIntake,
)
from ..services.twilio_gateway import normalize_us_phone, resolve_demo_connect_number
from ..services.retell_gateway import create_demo_phone_call
from ..services import demo_call_store

router = APIRouter()

LEAD_QUALIFY_ROLES = {"owner", "admin", "dispatcher"}
LEAD_BOOK_ROLES = {"owner", "admin", "dispatcher"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _ensure_user_role(current_user: User, allowed_roles: set[str], action: str) -> None:
    user_role = normalize_user_role(cast(str | None, current_user.role))
    if user_role not in allowed_roles:
        allowed = ", ".join(sorted(allowed_roles))
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' cannot {action}. Allowed roles: {allowed}.",
        )


def _resolve_org_for_intake(db: Session, *, org_id: int | None = None, intake_key: str | None = None) -> Organization:
    query = db.query(Organization)
    organization = None
    if org_id is not None:
        organization = query.filter(Organization.id == org_id).first()
    elif intake_key is not None:
        organization = query.filter(Organization.intake_key == intake_key).first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _create_intake_lead(db: Session, payload: LeadIntake, org_id: int):
    data = payload.model_dump()
    lead = create_lead(db, data, org_id)
    # Auto-schedule a follow-up reminder so the lead doesn't slip through the cracks.
    create_lead_followup_reminder(
        db,
        int(cast(int, lead.id)),
        org_id,
        lead_name=cast(str | None, lead.name),
    )
    return lead


def _attribution_lines(payload: PublicAttributionIn) -> list[str]:
    lines: list[str] = []
    for label, value in [
        ("CTA", payload.cta_name),
        ("Landing page", payload.landing_page),
        ("Referrer", payload.referrer_url),
        ("UTM source", payload.utm_source),
        ("UTM medium", payload.utm_medium),
        ("UTM campaign", payload.utm_campaign),
        ("UTM term", payload.utm_term),
        ("UTM content", payload.utm_content),
        ("GCLID", payload.gclid),
        ("MSCLKID", payload.msclkid),
        ("FBCLID", payload.fbclid),
    ]:
        if value:
            lines.append(f"{label}: {value}")
    if payload.raw_message:
        lines.append(payload.raw_message)
    return lines


def _create_public_tracking_lead(
    db: Session,
    *,
    org_id: int,
    source: str,
    payload: PublicAttributionIn,
    fallback_message: str,
):
    raw_lines = _attribution_lines(payload)
    raw_message = "\n".join([fallback_message, *raw_lines]).strip()
    lead_payload = {
        "name": getattr(payload, "name", None),
        "phone": normalize_us_phone(getattr(payload, "phone", None)),
        "email": getattr(payload, "email", None),
        "source": source,
        "raw_message": raw_message,
    }
    lead = create_lead(db, lead_payload, org_id)
    create_lead_followup_reminder(
        db,
        int(cast(int, lead.id)),
        org_id,
        lead_name=cast(str | None, lead.name),
        hours=0,
    )
    return lead


def _validate_demo_request(payload: DemoCallRequest) -> tuple[str, str, str]:
    name = (payload.name or "").strip()
    email = (payload.email or "").strip()
    phone = normalize_us_phone(payload.phone)
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Name must be at least 2 characters")
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Email must be a valid email address")
    if not phone.startswith("+") or len(re.sub(r"\D", "", phone)) < 11:
        raise HTTPException(status_code=422, detail="Phone must be a valid US phone number")
    return name, email, phone


def _sms_summary_body(name: str | None, extraction: dict) -> str:
    service = extraction.get("service_type") or "Service request"
    address = extraction.get("address") or "Not captured"
    urgency = extraction.get("urgency") or "Not captured"
    preferred_time = extraction.get("preferred_time") or "Not captured"
    notes = extraction.get("notes") or "No extra notes"
    greeting = f"Thanks for trying GoFieldwise, {name or 'there'}!"
    return (
        f"{greeting}\n"
        "Here's what Adrian captured:\n"
        f"Service: {service}\n"
        f"Address: {address}\n"
        f"Urgency: {urgency}\n"
        f"Preferred time: {preferred_time}\n"
        f"Notes: {notes}\n"
        "Ready to automate your front office? https://gofieldwise.com"
    )


def _demo_transcript(call_sid: str) -> list[dict[str, str]]:
    return [
        {
            "speaker": "adrian",
            "text": "Hi, this is Adrian with GoFieldwise. I can capture the job details and help route the request.",
        },
        {
            "speaker": "customer",
            "text": "I need help with a service request and want someone to follow up.",
        },
        {
            "speaker": "adrian",
            "text": f"Got it. I saved the request under demo call {call_sid} and alerted the team.",
        },
    ]


def _demo_twiml(name: str | None, connect_number: str) -> str:
    safe_name = html.escape((name or "there").strip() or "there")
    safe_connect_number = html.escape(connect_number)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say voice=\"alice\">Hi {safe_name}. This is Adrian, the GoFieldwise AI receptionist demo.</Say>"
        "<Pause length=\"1\"/>"
        "<Say voice=\"alice\">I am connecting you now.</Say>"
        "<Pause length=\"1\"/>"
        f"<Dial callerId=\"+16029320967\"><Number>{safe_connect_number}</Number></Dial>"
        "<Say voice=\"alice\">Thanks for trying the demo. Someone can follow up from the lead inbox.</Say>"
        "</Response>"
    )


def _twiml_url(request: Request, lead_id: int) -> str:
    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/api/demo-call/twiml/{lead_id}"


def _recover_missed_call_lead(db: Session, payload: MissedCallIntake, org_id: int) -> MissedCallRecoveryOut:
    raw_message = payload.raw_message
    if payload.call_sid:
        sid_line = f"Call SID: {payload.call_sid}"
        raw_message = f"{sid_line}\n{raw_message}" if raw_message else sid_line

    lead, created_new = upsert_missed_call_lead(
        db=db,
        organization_id=org_id,
        phone=payload.phone,
        name=payload.name,
        raw_message=raw_message,
    )
    reminder_created = False
    if created_new:
        # Missed calls are high urgency; nudge team immediately.
        create_lead_followup_reminder(
            db,
            int(cast(int, lead.id)),
            org_id,
            lead_name=cast(str | None, lead.name),
            hours=0,
        )
        reminder_created = True

    return MissedCallRecoveryOut(
        lead=lead,
        deduplicated=not created_new,
        reminder_created=reminder_created,
    )


# ---------------------------------------------------------------------------
# Public intake — no auth required.
# org_id routes the lead to the correct organization (e.g. from a web form
# embed or missed-call webhook). In production, harden with a per-org
# webhook token; for now org_id is the routing key.
# ---------------------------------------------------------------------------

@router.post(
    "/leads/intake/{org_id}",
    response_model=LeadOut,
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake(org_id: int, payload: LeadIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, org_id=org_id)
    return _create_intake_lead(db, payload, int(cast(int, org.id)))


@router.post(
    "/leads/intake/by-key/{intake_key}",
    response_model=LeadOut,
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake_by_key(intake_key: str, payload: LeadIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, intake_key=intake_key)
    return _create_intake_lead(db, payload, int(cast(int, org.id)))


@router.post(
    "/leads/intake/demo-call/{org_id}",
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake_demo_call(
    org_id: int,
    payload: DemoCallIntake,
    request: Request,
    db: Session = Depends(get_db),
):
    demo_payload = DemoCallRequest(name=payload.name, email=payload.email, phone=payload.phone)
    name, email, phone = _validate_demo_request(demo_payload)
    org = _resolve_org_for_intake(db, org_id=org_id)
    payload.name = name
    payload.email = email
    payload.phone = phone
    lead = _create_public_tracking_lead(
        db,
        org_id=int(cast(int, org.id)),
        source="demo_call",
        payload=payload,
        fallback_message="Demo call request captured from gofieldwise.com.",
    )
    lead_id = int(cast(int, lead.id))
    call_started, retell_call, call_error = create_demo_phone_call(
        db,
        organization_id=int(cast(int, org.id)),
        to_number=phone,
        caller_name=name,
        caller_email=email,
        lead_id=lead_id,
    )
    call_sid = str((retell_call or {}).get("call_id") or f"DEMO{lead_id}")
    demo_call_store.upsert_call(
        call_sid,
        {
            "lead_id": lead_id,
            "organization_id": int(cast(int, org.id)),
            "name": name,
            "email": email,
            "phone": phone,
            "metadata": {"demo_mode": True},
            "retell_response": retell_call,
        },
    )
    return {
        "ok": True,
        "lead_id": lead_id,
        "call_started": call_started,
        "call_sid": call_sid,
        "call_error": call_error,
        "message": (
            "Demo call started."
            if call_started
            else "Demo request captured. The team can follow up from the lead inbox."
        ),
    }


@router.post(
    "/leads/intake/demo-call/by-key/{intake_key}",
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake_demo_call_by_key(
    intake_key: str,
    payload: DemoCallIntake,
    request: Request,
    db: Session = Depends(get_db),
):
    org = _resolve_org_for_intake(db, intake_key=intake_key)
    return intake_demo_call(int(cast(int, org.id)), payload, request, db)


@router.post("/demo/call", status_code=status.HTTP_201_CREATED, tags=["demo"])
def start_demo_call(payload: DemoCallRequest, request: Request, db: Session = Depends(get_db)):
    org_id = int(request.query_params.get("org_id", "1"))
    compat_payload = DemoCallIntake(name=payload.name, email=payload.email, phone=payload.phone)
    return intake_demo_call(org_id, compat_payload, request, db)


@router.post(
    "/leads/intake/intent/{org_id}",
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake_intent(org_id: int, payload: IntentIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, org_id=org_id)
    lead = _create_public_tracking_lead(
        db,
        org_id=int(cast(int, org.id)),
        source="web_intent",
        payload=payload,
        fallback_message="Website intent click captured from gofieldwise.com.",
    )
    return {"ok": True, "lead_id": int(cast(int, lead.id))}


@router.post(
    "/leads/intake/intent/by-key/{intake_key}",
    status_code=status.HTTP_201_CREATED,
    tags=["intake"],
)
def intake_intent_by_key(intake_key: str, payload: IntentIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, intake_key=intake_key)
    return intake_intent(int(cast(int, org.id)), payload, db)


@router.post(
    "/leads/intake/support-chat/{org_id}",
    tags=["intake"],
)
def intake_support_chat(org_id: int, payload: SupportChatIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, org_id=org_id)
    limit = min(max(payload.limit, 1), 5)
    answers = [
        "GoFieldwise captures calls and web leads so the shop can follow up fast.",
        "The platform keeps jobs, reminders, dispatch, and customer communication organized in one workflow.",
        "For setup, the next best step is to request a demo call or call (602) 932-0967.",
    ][:limit]
    lead = create_lead(
        db,
        {
            "name": "Website support chat",
            "source": "support_chat",
            "raw_message": (
                f"Support chat question: {payload.message}\n"
                f"Context: {payload.context_key or 'general'}\n"
                f"Trade: {payload.trade or 'general'}"
            ),
        },
        int(cast(int, org.id)),
    )
    return {
        "ok": True,
        "lead_id": int(cast(int, lead.id)),
        "answers": answers,
        "messages": [{"speaker": "adrian", "text": answer} for answer in answers],
    }


@router.post(
    "/leads/intake/support-chat/by-key/{intake_key}",
    tags=["intake"],
)
def intake_support_chat_by_key(intake_key: str, payload: SupportChatIntake, db: Session = Depends(get_db)):
    org = _resolve_org_for_intake(db, intake_key=intake_key)
    return intake_support_chat(int(cast(int, org.id)), payload, db)


@router.get("/demo-call/transcript/{call_sid}", tags=["intake"])
def demo_call_transcript(call_sid: str):
    record = demo_call_store.get_call(call_sid)
    return {
        "ok": True,
        "call_sid": call_sid,
        "transcript": (record or {}).get("transcript") or _demo_transcript(call_sid),
    }


@router.get("/demo/transcript-stream/{call_id}", tags=["demo"])
def demo_transcript_stream(call_id: str):
    q = demo_call_store.subscribe(call_id)

    def events():
        try:
            yield f"event: connected\ndata: {json.dumps({'call_id': call_id})}\n\n"
            while True:
                event = demo_call_store.next_event(q)
                if event is None:
                    yield f"event: ping\ndata: {json.dumps({'call_id': call_id})}\n\n"
                    continue
                event_name = str(event.get("event") or "message")
                yield f"event: {event_name}\ndata: {json.dumps(event)}\n\n"
                if event_name == "call_ended":
                    break
        finally:
            demo_call_store.unsubscribe(call_id, q)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/retell/inbound-call", tags=["retell"])
def retell_inbound_call(payload: RetellInboundCallIn):
    return {
        "tenant_id": "demo",
        "agent_override": None,
        "variables": {
            "business_name": "GoFieldwise",
            "trade": "home services",
            "hours": "Mon-Fri 8-5",
            "service_area": "OKC and surrounding areas",
            "pricing": "Starting at $200/mo",
            "emergency_rules": "Same-day for active leaks",
            "booking_url": "https://gofieldwise.com/book",
            "review_url": "https://gofieldwise.com/reviews",
        },
    }


@router.post("/retell/events", tags=["retell"])
def retell_events(payload: RetellEventIn, db: Session = Depends(get_db)):
    event = payload.event
    call_id = payload.call_id
    update = {
        "call_status": payload.call_status,
        "recording_url": payload.recording_url,
        "duration": payload.duration,
        "quality_score": payload.quality_score,
    }
    if payload.metadata is not None:
        update["metadata"] = payload.metadata
    record = demo_call_store.upsert_call(call_id, update)

    if payload.transcript is not None:
        demo_call_store.append_transcript(call_id, payload.transcript)
        demo_call_store.publish(call_id, "transcript", {"transcript": payload.transcript})

    if event == "call_ended":
        extraction = payload.ai_anthropic_extraction or {}
        demo_call_store.upsert_call(call_id, {"extraction": extraction})
        demo_call_store.publish(call_id, "call_ended", {"extraction": extraction})
        metadata = record.get("metadata") or {}
        if metadata.get("demo_mode") is True and record.get("phone") and extraction:
            from ..services.twilio_gateway import send_sms_message

            send_sms_message(
                db,
                organization_id=int(record.get("organization_id") or 1),
                to_phone=str(record["phone"]),
                body=_sms_summary_body(record.get("name"), extraction),
            )
    else:
        demo_call_store.publish(call_id, event, payload.model_dump(exclude_none=True))

    return {"ok": True, "call_id": call_id, "event": event}


@router.get("/demo-call/twiml/{lead_id}", tags=["intake"])
def demo_call_twiml(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    name = cast(str | None, lead.name) if lead else None
    organization_id = int(cast(int, lead.organization_id)) if lead else 0
    connect_number = resolve_demo_connect_number(db, organization_id) if organization_id else "+16029320967"
    return Response(content=_demo_twiml(name, connect_number), media_type="application/xml")


@router.post("/demo-call/send-summary/{call_sid}", tags=["intake"])
def send_demo_call_summary(call_sid: str):
    return {
        "ok": True,
        "call_sid": call_sid,
        "to": "(602) 932-0967",
        "sent": False,
        "message": "Demo summary queued for follow-up.",
    }


@router.post(
    "/leads/intake/missed-call/{org_id}",
    response_model=MissedCallRecoveryOut,
    status_code=status.HTTP_200_OK,
    tags=["intake"],
)
def intake_missed_call(
    org_id: int,
    payload: MissedCallIntake,
    db: Session = Depends(get_db),
):
    """Recover missed calls quickly with dedupe to avoid duplicate lead spam."""
    org = _resolve_org_for_intake(db, org_id=org_id)
    return _recover_missed_call_lead(db, payload, int(cast(int, org.id)))


@router.post(
    "/leads/intake/missed-call/by-key/{intake_key}",
    response_model=MissedCallRecoveryOut,
    status_code=status.HTTP_200_OK,
    tags=["intake"],
)
def intake_missed_call_by_key(
    intake_key: str,
    payload: MissedCallIntake,
    db: Session = Depends(get_db),
):
    org = _resolve_org_for_intake(db, intake_key=intake_key)
    return _recover_missed_call_lead(db, payload, int(cast(int, org.id)))


# ---------------------------------------------------------------------------
# Authenticated lead management
# ---------------------------------------------------------------------------

@router.get("/leads", response_model=List[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    return get_leads(db, org_id)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead_api(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(
    lead_id: int,
    update: LeadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead, error = transition_lead_status(
        db,
        lead,
        update.status,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return lead


@router.post("/leads/{lead_id}/convert", response_model=LeadConvertOut)
def convert_lead_api(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        lead, customer, job = convert_lead(
            db,
            lead,
            org_id,
            actor_user_id=int(cast(int, current_user.id)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return LeadConvertOut(
        lead_id=int(cast(int, lead.id)),
        customer_id=int(cast(int, customer.id)),
        job_id=int(cast(int, job.id)),
    )


@router.post("/leads/{lead_id}/qualify", response_model=LeadQualificationOut)
def qualify_lead_api(
    lead_id: int,
    payload: LeadQualificationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_user_role(current_user, LEAD_QUALIFY_ROLES, "qualify leads")

    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead, error = qualify_lead(
        db,
        lead,
        emergency=payload.emergency,
        budget_confirmed=payload.budget_confirmed,
        requested_within_48h=payload.requested_within_48h,
        service_category=payload.service_category,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)

    create_lead_booking_reminder(
        db,
        lead_id=int(cast(int, lead.id)),
        organization_id=org_id,
        lead_name=cast(str | None, lead.name),
    )
    return LeadQualificationOut(lead=lead, booking_reminder_created=True)


@router.post("/leads/{lead_id}/book", response_model=LeadBookOut)
def book_lead_api(
    lead_id: int,
    payload: LeadBookInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_user_role(current_user, LEAD_BOOK_ROLES, "book leads")

    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    booked_lead, customer, job, dismissed_count, error = book_lead(
        db,
        lead,
        org_id,
        payload.technician_id,
        payload.scheduled_time,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    if not booked_lead or not customer or not job:
        raise HTTPException(status_code=500, detail="Lead booking failed unexpectedly")

    return LeadBookOut(
        lead_id=int(cast(int, booked_lead.id)),
        customer_id=int(cast(int, customer.id)),
        job_id=int(cast(int, job.id)),
        job_status=str(cast(str, job.status)),
        scheduled_time=cast(datetime, job.scheduled_time),
        technician_id=int(cast(int, job.technician_id)),
        booking_reminders_dismissed=dismissed_count,
    )


@router.get("/leads/{lead_id}/activity", response_model=List[LeadActivityOut])
def get_lead_activity_api(
    lead_id: int,
    action: str | None = Query(None),
    since_hours: int | None = Query(None, ge=1, le=720),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = int(cast(int, current_user.organization_id))
    lead = get_lead(db, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return list_lead_activities(
        db,
        lead_id,
        org_id,
        action=action,
        since_hours=since_hours,
    )
