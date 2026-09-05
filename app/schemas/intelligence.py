from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class PriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class ActionItemStatusEnum(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class SeverityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TopicSchema(BaseModel):
    title: str = Field(description="Clear title of the topic discussed")
    summary: str = Field(description="Summary of the points covered under this topic")
    importance: int = Field(default=1, ge=1, le=5, description="Relative importance ranking from 1 to 5")

class DecisionSchema(BaseModel):
    decision: str = Field(description="Clear statement of what was formally agreed or decided")
    context: Optional[str] = Field(default=None, description="Background or reasoning behind the decision")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    source_segment_id: Optional[str] = Field(default=None, description="UUID of the transcript segment supporting this decision")

class ActionItemSchema(BaseModel):
    description: str = Field(description="Actionable task description")
    assignee_name: Optional[str] = Field(default=None, description="Name of the person assigned")
    deadline: Optional[str] = Field(default=None, description="ISO-8601 date deadline if specified in transcript")
    priority: PriorityEnum = Field(default=PriorityEnum.MEDIUM)
    status: ActionItemStatusEnum = Field(default=ActionItemStatusEnum.PENDING)
    source_segment_id: Optional[str] = Field(default=None, description="UUID of the transcript segment supporting this action")

class RiskSchema(BaseModel):
    description: str = Field(description="Identified obstacle, technical risk, or project blocker")
    severity: SeverityEnum = Field(default=SeverityEnum.MEDIUM)
    source_segment_id: Optional[str] = Field(default=None, description="UUID of the transcript segment identifying this risk")

class OpenQuestionSchema(BaseModel):
    question: str = Field(description="Unresolved question or pending inquiry raised during the meeting")
    owner: Optional[str] = Field(default=None, description="Person responsible for finding the answer")
    resolved: bool = Field(default=False)
    source_segment_id: Optional[str] = Field(default=None, description="UUID of the transcript segment")

class MeetingIntelligenceSchema(BaseModel):
    executive_summary: str = Field(description="High-level 2-3 paragraph executive summary of the meeting")
    summary: str = Field(description="Detailed narrative summary organized chronologically or by agenda")
    topics: List[TopicSchema] = Field(default_factory=list)
    decisions: List[DecisionSchema] = Field(default_factory=list)
    action_items: List[ActionItemSchema] = Field(default_factory=list)
    risks: List[RiskSchema] = Field(default_factory=list)
    open_questions: List[OpenQuestionSchema] = Field(default_factory=list)
