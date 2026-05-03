from __future__ import annotations

from queue import Empty, Queue
from threading import Lock
from typing import Any


_lock = Lock()
_records: dict[str, dict[str, Any]] = {}
_subscribers: dict[str, list[Queue]] = {}


def upsert_call(call_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        record = _records.get(call_id, {})
        record.update(data)
        record["call_id"] = call_id
        _records[call_id] = record
        return dict(record)


def get_call(call_id: str) -> dict[str, Any] | None:
    with _lock:
        record = _records.get(call_id)
        return dict(record) if record else None


def append_transcript(call_id: str, transcript: list[dict[str, Any]]) -> None:
    with _lock:
        record = _records.setdefault(call_id, {"call_id": call_id})
        record["transcript"] = transcript


def subscribe(call_id: str) -> Queue:
    q: Queue = Queue()
    with _lock:
        _subscribers.setdefault(call_id, []).append(q)
        record = _records.get(call_id)
    if record and record.get("transcript"):
        q.put({"event": "transcript", "call_id": call_id, "transcript": record["transcript"]})
    return q


def unsubscribe(call_id: str, q: Queue) -> None:
    with _lock:
        queues = _subscribers.get(call_id, [])
        if q in queues:
            queues.remove(q)
        if not queues:
            _subscribers.pop(call_id, None)


def publish(call_id: str, event_name: str, payload: dict[str, Any]) -> None:
    with _lock:
        subscribers = list(_subscribers.get(call_id, []))
    event = {"event": event_name, "call_id": call_id, **payload}
    for q in subscribers:
        q.put(event)


def next_event(q: Queue, timeout: float = 15.0) -> dict[str, Any] | None:
    try:
        return q.get(timeout=timeout)
    except Empty:
        return None
