from datetime import date, datetime
from pydantic import BaseModel

class Dose(BaseModel):
    dose_label: str
    vaccine_name: str
    dose_date: date

class Disease(BaseModel):
    disease_name: str
    doses_received: list[Dose]
    doses_completed_count: int
    doses_expected_count: int | None = None
    completion_status: str
    missing_doses: list[str]

class PatientLedger(BaseModel):
    user_id: str
    patient_name: str
    generated_at: datetime
    ledger: list[Disease]

