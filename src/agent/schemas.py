from pydantic import BaseModel, Field


class ExceptionDiagnosis(BaseModel):
    order_id: str = Field(default="UNKNOWN")
    root_cause: str = Field(description = "Must be one of: TAX_MISMATCH, FEE_SPIKE, MISSING_UTR, BANK_DEDUCTION, ORPHAN_BANK_CREDIT, UNKNOWN")
    explanation: str = Field(description="One clear sentence explaining the mathematical variance.")
    suggested_adjustment_inr: float = Field(description="The INR amount needed to balance the ledger. 0 if none.")

class ChatRequest(BaseModel):
    question: str
    batch_id: str