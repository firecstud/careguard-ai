from typing import List, Optional

from pydantic import BaseModel, Field


class Utterance(BaseModel):
    speaker: str
    text: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    speaker_id: Optional[int] = None


class Transcript(BaseModel):
    session_id: str
    audio_file: Optional[str] = None
    utterances: List[Utterance]


class LiabilityFlag(BaseModel):
    category: str
    severity: str
    patient_quote: str
    detection_method: str
    what_was_missed: str
    what_should_have_been_said: str
    therapist_failure_description: Optional[str] = None
    utterance_index: int
    timestamp: Optional[str] = None
    patient_intent: Optional[str] = None
    risk_reasoning: Optional[str] = None
    risk_indicators: List[str] = Field(default_factory=list)
    patient_confidence: Optional[float] = None
    adequacy_rating: Optional[str] = None
    therapist_quote: Optional[str] = None


class AnalysisMetadata(BaseModel):
    patient_stage: str
    therapist_stage: str
    warnings: List[str] = Field(default_factory=list)


class LiabilityReport(BaseModel):
    session_id: str
    overall_risk_score: int
    risk_level: str
    flags: List[LiabilityFlag]
    analysis_metadata: Optional[AnalysisMetadata] = None
