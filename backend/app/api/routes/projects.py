from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Project
from app.schemas.project import (
    ParticipantPersonalityPatchRequest,
    ParticipantPersonalityResponse,
    ParticipantImportRequest,
    PersonalityPresetApplyRequest,
    PersonalityPresetSummary,
    ProjectParticipantsResponse,
    ParticipantSummary,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
)
from app.services.simulation.service import (
    apply_preset_to_project_participants,
    calculate_personality_changed_fields,
    create_project,
    get_project_or_404,
    get_project_participant_or_404,
    import_participants,
    list_personality_presets,
    update_project_participant_personality,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = create_project(db, payload)
    return serialize_project(project)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project_endpoint(project_id: str, db: Session = Depends(get_db)) -> ProjectDetailResponse:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return serialize_project_detail(project)


@router.post("/{project_id}/participants/import", response_model=ProjectDetailResponse)
def import_participants_endpoint(
    project_id: str,
    payload: ParticipantImportRequest,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    import_participants(db, project, payload)
    db.refresh(project)
    return serialize_project_detail(project)


@router.get("/{project_id}/participants", response_model=ProjectParticipantsResponse)
def list_project_participants_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectParticipantsResponse:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return serialize_project_participants(project, db)


@router.get(
    "/{project_id}/participants/{participant_id}/personality",
    response_model=ParticipantPersonalityResponse,
)
def get_participant_personality_endpoint(
    project_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
) -> ParticipantPersonalityResponse:
    participant = get_project_participant_or_404(db, project_id, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found.")
    return serialize_participant_personality(participant)


@router.patch(
    "/{project_id}/participants/{participant_id}/personality",
    response_model=ParticipantPersonalityResponse,
)
def patch_participant_personality_endpoint(
    project_id: str,
    participant_id: str,
    payload: ParticipantPersonalityPatchRequest,
    db: Session = Depends(get_db),
) -> ParticipantPersonalityResponse:
    participant = get_project_participant_or_404(db, project_id, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found.")
    participant = update_project_participant_personality(
        db,
        participant,
        payload.editable_personality.model_dump(),
    )
    return serialize_participant_personality(participant)


@router.get("/{project_id}/personality-presets", response_model=list[PersonalityPresetSummary])
def list_personality_presets_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
) -> list[PersonalityPresetSummary]:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return [
        PersonalityPresetSummary(
            slug=preset.slug,
            name=preset.name,
            description=preset.description,
            values=preset.values,
        )
        for preset in list_personality_presets(db)
    ]


@router.post("/{project_id}/personality-presets/apply", response_model=ProjectParticipantsResponse)
def apply_personality_preset_endpoint(
    project_id: str,
    payload: PersonalityPresetApplyRequest,
    db: Session = Depends(get_db),
) -> ProjectParticipantsResponse:
    project = get_project_or_404(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        apply_preset_to_project_participants(db, project, payload.preset_slug, payload.participant_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(project)
    return serialize_project_participants(project, db)


def serialize_project(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        participant_count=len(project.participants),
        created_at=project.created_at,
    )


def serialize_project_detail(project: Project) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        **serialize_project(project).model_dump(),
        participants=build_participant_summaries(project),
    )


def serialize_project_participants(project: Project, db: Session) -> ProjectParticipantsResponse:
    return ProjectParticipantsResponse(
        project_id=project.id,
        project_name=project.name,
        participants=build_participant_summaries(project),
        presets=[
            PersonalityPresetSummary(
                slug=preset.slug,
                name=preset.name,
                description=preset.description,
                values=preset.values,
            )
            for preset in list_personality_presets(db)
        ],
    )


def build_participant_summaries(project: Project) -> list[ParticipantSummary]:
    return [
        ParticipantSummary(
            id=participant.id,
            name=participant.name,
            cast_role=participant.cast_role,
            city=participant.city,
            occupation=participant.occupation,
            attachment_style=participant.attachment_style,
            display_order=participant.display_order,
            editable_personality=participant.editable_personality,
        )
        for participant in sorted(project.participants, key=lambda item: item.display_order)
    ]


def serialize_participant_personality(participant) -> ParticipantPersonalityResponse:
    return ParticipantPersonalityResponse(
        participant_id=participant.id,
        name=participant.name,
        cast_role=participant.cast_role,
        editable_personality=participant.editable_personality,
        changed_fields=calculate_personality_changed_fields(
            participant.imported_payload,
            participant.editable_personality,
        ),
    )
