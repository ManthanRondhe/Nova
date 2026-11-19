"""
Schemas for AI-Powered Visual Repair Assistance System
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RepairStep(BaseModel):
    step_number: int = Field(..., description="Chronological step number")
    title: str = Field(..., description="Concise, actionable step title")
    instruction: str = Field(..., description="Detailed technical instructions for mechanic")
    image_search_query: str = Field(..., description="Search query for technical diagram or photograph")
    image_url: Optional[str] = Field(None, description="Direct URL of verified technical image or placeholder")
    image_source: Optional[str] = Field(None, description="Attribution / license source of the image")
    warning: Optional[str] = Field(None, description="Critical safety warning or caution for this step")


class RepairGuide(BaseModel):
    repair_title: str = Field(..., description="Title of the repair operation")
    predicted_fault: str = Field(..., description="Diagnosed potential fault name")
    fault_explanation: str = Field(..., description="Clear explanation of how the fault occurs and its symptoms")
    difficulty: str = Field("Intermediate", description="Skill level required: Beginner, Intermediate, Advanced, Professional")
    estimated_time: Optional[str] = Field(None, description="Estimated repair duration, e.g. 1.5 - 2.5 hours")
    vehicle_context: Optional[str] = Field("Standard Vehicle", description="Target vehicle make, model, year context")
    required_tools: List[str] = Field(default_factory=list, description="List of essential tools, PPE, and test instruments")
    safety_precautions: List[str] = Field(default_factory=list, description="Pre-repair mandatory safety precautions")
    repair_steps: List[RepairStep] = Field(default_factory=list, description="Ordered step-by-step repair instructions")
    final_verification: List[str] = Field(default_factory=list, description="Post-repair functional verification and testing procedures")
    generated_at: Optional[str] = Field(None, description="ISO timestamp of guide generation")
    source_type: Optional[str] = Field("ai_generated", description="Generator source: llm_gemini, llm_openai, domain_expert")
    disclaimer: Optional[str] = Field(
        "AI-assisted technical guidance. Always verify factory torque specifications and safety procedures in vehicle manufacturer service documentation.",
        description="Engineering and liability disclaimer"
    )


class RepairGuideRequest(BaseModel):
    predicted_fault: str = Field(..., description="Name of the predicted fault (e.g. Starter Motor Solenoid Failure)")
    vehicle_make: Optional[str] = Field("", description="Vehicle manufacturer (e.g. Maruti, Honda, Toyota, Hyundai)")
    vehicle_model: Optional[str] = Field("", description="Vehicle model (e.g. Swift, City, Creta)")
    vehicle_year: Optional[int] = Field(None, description="Manufacturing year (e.g. 2022)")
    engine_variant: Optional[str] = Field("", description="Engine variant / fuel type (e.g. 1.2L DualJet Petrol, 1.5L Diesel)")
    symptoms: Optional[str] = Field("", description="Observed symptoms or mechanic complaints")
    diagnostic_findings: Optional[str] = Field("", description="Diagnostic scan findings, multimeter readings, or notes")
    fix_procedure: Optional[str] = Field("", description="Initial fix procedure from diagnosis engine")
    system: Optional[str] = Field("", description="Automotive system category (e.g. Electrical, Cooling, Brakes)")


class RepairGuideResponse(BaseModel):
    success: bool
    repair_guide: Optional[RepairGuide] = None
    error: Optional[str] = None
