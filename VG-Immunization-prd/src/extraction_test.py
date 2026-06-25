import json
with open("data/ledger_example.json", "r") as f:
    ledger_list = json.load(f)

ledger = ledger_list[0]
def test_required_fields(ledger):
    assert "user_id" in ledger
    assert "patient_name" in ledger
    assert "generated_at" in ledger
    assert "ledger" in ledger

def test_patient_name(ledger):
    assert ledger["patient_name"] is not None

def test_every_disease_has_name(ledger):
    for disease in ledger["ledger"]:
        assert disease["disease_name"] != ""

def test_completed_count(ledger):
    for disease in ledger["ledger"]:
        actual = len(disease["doses_received"])
        assert actual == disease["doses_completed_count"]

for i, ledger in enumerate(ledger_list):
    test_required_fields(ledger)
    test_patient_name(ledger)
    test_every_disease_has_name(ledger)
    test_completed_count(ledger)
    print(f"  ✓ all tests passed")

print("\nAll records passed!")