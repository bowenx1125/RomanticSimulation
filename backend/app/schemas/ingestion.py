from pydantic import BaseModel, Field


class WeChatIngestRequest(BaseModel):
    project_id: str
    file_path: str


class WeChatFileSummary(BaseModel):
    file_path: str
    participant_name: str


class WeChatFileListResponse(BaseModel):
    files: list[WeChatFileSummary] = Field(default_factory=list)


class WeChatIngestResponse(BaseModel):
    status: str
    participant_id: str
    personality_summary: dict = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
