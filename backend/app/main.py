from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .database import Base, engine, get_db
from .models import Finding, Note
from .schemas import FindingCreate, FindingOut, NoteCreate, NoteOut, StatusUpdate
from .worker import verify_finding

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Triagely API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

VALID_STATUSES = {"new", "verifying", "confirmed", "refuted", "fixed"}
VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/findings", response_model=FindingOut)
def create_finding(payload: FindingCreate, db: Session = Depends(get_db)):
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(400, "Invalid severity")
    item = Finding(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.get("/findings", response_model=list[FindingOut])
def list_findings(status: str | None = None, severity: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Finding).order_by(Finding.created_at.desc())
    if status: stmt = stmt.where(Finding.status == status)
    if severity: stmt = stmt.where(Finding.severity == severity)
    return list(db.scalars(stmt).all())

@app.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: int, db: Session = Depends(get_db)):
    item = db.get(Finding, finding_id)
    if not item: raise HTTPException(404, "Finding not found")
    return item

@app.patch("/findings/{finding_id}/status", response_model=FindingOut)
def update_status(finding_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in VALID_STATUSES: raise HTTPException(400, "Invalid status")
    item = db.get(Finding, finding_id)
    if not item: raise HTTPException(404, "Finding not found")
    item.status = payload.status
    item.resolved_at = datetime.now(timezone.utc) if payload.status == "fixed" else None
    db.commit(); db.refresh(item)
    if payload.status == "verifying":
        verify_finding.delay(item.id)
    return item

@app.post("/findings/{finding_id}/notes", response_model=NoteOut)
def add_note(finding_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    if not db.get(Finding, finding_id): raise HTTPException(404, "Finding not found")
    note = Note(finding_id=finding_id, **payload.model_dump())
    db.add(note); db.commit(); db.refresh(note)
    return note

@app.get("/findings/{finding_id}/notes", response_model=list[NoteOut])
def list_notes(finding_id: int, db: Session = Depends(get_db)):
    if not db.get(Finding, finding_id): raise HTTPException(404, "Finding not found")
    return list(db.scalars(select(Note).where(Note.finding_id == finding_id).order_by(Note.created_at)).all())

@app.post("/findings/import/sarif")
def import_sarif(payload: dict, db: Session = Depends(get_db)):
    imported = 0
    for run in payload.get("runs", []):
        tool = run.get("tool", {}).get("driver", {}).get("name", "SARIF")
        rules = {r.get("id"): r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")
            rule = rules.get(rule_id, {})
            loc = (result.get("locations") or [{}])[0].get("physicalLocation", {})
            artifact = loc.get("artifactLocation", {}).get("uri", "")
            region = loc.get("region", {})
            level = result.get("level", "warning")
            severity = {"error": "high", "warning": "medium", "note": "low", "none": "info"}.get(level, "medium")
            message = result.get("message", {}).get("text", rule.get("shortDescription", {}).get("text", ""))
            fp = (result.get("fingerprints") or {}).get("primaryLocationLineHash", f"{tool}:{rule_id}:{artifact}:{region.get('startLine','')}")
            exists = db.scalar(select(Finding).where(Finding.fingerprint == fp))
            if exists: continue
            db.add(Finding(title=rule.get("shortDescription", {}).get("text", rule_id), description=message,
                           severity=severity, tool=tool, rule_id=rule_id, file_path=artifact,
                           fingerprint=fp, evidence={"line": region.get("startLine"), "message": message}))
            imported += 1
    db.commit()
    return {"imported": imported, "message": "SARIF processed; duplicate fingerprints skipped."}

@app.post("/findings/demo")
def seed_demo(db: Session = Depends(get_db)):
    samples = [
        ("SQL query built from user input", "critical", "semgrep", "python.lang.security.audit.sql-injection"),
        ("Dependency has a known CVE", "high", "pip-audit", "PYSEC-2024-001"),
        ("Debug endpoint exposes configuration", "medium", "manual", "debug-config"),
        ("Unpinned GitHub Action", "low", "semgrep", "unpinned-action"),
    ]
    made = 0
    for title, severity, tool, rule in samples:
        if not db.scalar(select(Finding).where(Finding.rule_id == rule)):
            db.add(Finding(title=title, description="Demo finding — inspect the evidence and record a triage decision.",
                           severity=severity, tool=tool, rule_id=rule, file_path="src/example.py",
                           fingerprint=f"demo:{rule}", evidence={"source": "demo dataset"}))
            made += 1
    db.commit()
    return {"created": made}

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    counts = {s: db.scalar(select(func.count()).select_from(Finding).where(Finding.severity == s)) or 0 for s in VALID_SEVERITIES}
    fixed = list(db.scalars(select(Finding).where(Finding.status == "fixed", Finding.resolved_at.is_not(None))).all())
    durations = [(x.resolved_at - x.created_at).total_seconds() / 3600 for x in fixed if x.resolved_at and x.created_at]
    return {"severity": counts, "total": sum(counts.values()), "fixed": len(fixed),
            "mean_time_to_resolve_hours": round(sum(durations)/len(durations), 1) if durations else None}
