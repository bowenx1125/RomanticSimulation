from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ParticipantProfile
from app.schemas.ingestion import (
    WeChatFileListResponse,
    WeChatFileSummary,
    WeChatIngestRequest,
    WeChatIngestResponse,
)
from app.services.simulation.service import create_project_participant, get_project_or_404
from ingestion.wechat_ingest import build_participant_payload_from_markdown


router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.get("/wechat/files", response_model=WeChatFileListResponse)
def list_wechat_markdown_files() -> WeChatFileListResponse:
    search_roots = [Path.cwd() / "wechat_data", Path.cwd().parent / "wechat_data"]
    root = next((candidate for candidate in search_roots if candidate.exists() and candidate.is_dir()), None)
    if root is None:
        return WeChatFileListResponse(files=[])

    files = [
        WeChatFileSummary(
            file_path=str(Path("wechat_data") / path.name),
            participant_name=path.stem,
        )
        for path in sorted(root.glob("*.md"))
    ]
    return WeChatFileListResponse(files=files)


@router.post("/wechat", response_model=WeChatIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_wechat_markdown(
    payload: WeChatIngestRequest,
    db: Session = Depends(get_db),
) -> WeChatIngestResponse:
    project = get_project_or_404(db, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    resolved_path = resolve_input_file(payload.file_path)
    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {payload.file_path}")

    steps = [
        "Parsing markdown...",
        "Extracting features...",
        "Generating personality...",
        "Creating participant...",
    ]

    markdown_text = resolved_path.read_text(encoding="utf-8")
    ingest_result, participant_payload = build_participant_payload_from_markdown(
        payload.file_path,
        markdown_text,
    )
    existing = db.scalar(
        select(ParticipantProfile).where(
            ParticipantProfile.project_id == project.id,
            ParticipantProfile.name == participant_payload.name,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Participant '{participant_payload.name}' already exists in this project.",
        )
    participant = create_project_participant(db, project, participant_payload)

    return WeChatIngestResponse(
        status="success",
        participant_id=participant.id,
        personality_summary=ingest_result.personality_summary,
        steps=steps,
    )


def resolve_input_file(file_path: str) -> Path:
    candidate = Path(file_path)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate

    parent_candidate = Path.cwd().parent / candidate
    if parent_candidate.exists():
        return parent_candidate

    return cwd_candidate
