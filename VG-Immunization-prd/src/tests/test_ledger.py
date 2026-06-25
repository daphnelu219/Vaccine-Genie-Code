import json
from schema import PatientLedger
from pydantic import ValidationError

with open("data/ledger_example.json", "r") as f:
    ledger_list = json.load(f)

ledger = ledger_list[0]
def test_required_fields():
    assert "user_id" in ledger
    assert "patient_name" in ledger
    assert "generated_at" in ledger
    assert "ledger" in ledger

def test_patient_name():
    assert ledger["patient_name"] is not None

def test_every_disease_has_name():
    for disease in ledger["ledger"]:
        assert disease["disease_name"] != ""

def test_completed_count():
    for disease in ledger["ledger"]:
        actual = len(disease["doses_received"])
        assert actual == disease["doses_completed_count"]

def test_pydantic_schema():
    try:
        PatientLedger.model_validate(ledger)
        print("  ✓ pydantic schema valid")
    except ValidationError as e:
        raise AssertionError(f"Schema validation failed: {e}")
    
