import json
import pandas as pd
from collections import defaultdict
from google import genai
from google.genai import types
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from dotenv import load_dotenv
import os

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

with open('data/extracted_records.json', 'r') as file:
    data = json.load(file)
df = pd.DataFrame(data)

with open("data/vaccine_mapping.json", "r") as f:
    vaccine_map = json.load(f)

# build lowercase version
vaccine_map_lower = {k.lower(): v for k, v in vaccine_map.items()}

def lookup_vaccine(vaccine_name):
    # strip dose indicators like "#1", "#2" before lookup
    cleaned = vaccine_name.strip().lower()
    cleaned = cleaned.replace("#1", "").replace("#2", "").replace("#3", "").strip()
    return vaccine_map_lower.get(cleaned)


load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options={"api_version": "v1"})

# Step 1 — Load CDC page
loader = WebBaseLoader("https://www.cdc.gov/vaccines/imz-schedules/adult-easyread.html")
docs = loader.load()

# Step 2 — Chunk it
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# Step 3 — Embed and store
class GeminiEmbeddings:
    def embed_documents(self, texts):
        result = client.models.embed_content(
            model="text-embedding-004",
            contents=texts
        )
        return [e.values for e in result.embeddings]
    
    def embed_query(self, text):
        result = client.models.embed_content(
            model="gemini-embedding-2",
            contents=[text]
        )
        return result.embeddings[0].values

embeddings = GeminiEmbeddings()

# now use it with Chroma as before
if not os.path.exists("data/cdc_vectorstore"):
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory="data/cdc_vectorstore")
else:
    vectorstore = Chroma(persist_directory="data/cdc_vectorstore", embedding_function=embeddings)

# Step 4 — Query at runtime
def check_compliance(patient_ledger):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    relevant_docs = retriever.invoke(f"vaccine requirements compliance {patient_ledger}")
    context = "\n".join([doc.page_content for doc in relevant_docs])
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"""
        Based on the CDC immunization schedule:
        {context}
        
        Based on the CDC immunization schedule, is this patient compliant?
        Patient ledger: {patient_ledger}
        
        Take the given JSON file and for each disease fill in the attributes completion_status and missing_doses for each patient.
        Return ONLY the updated JSON array. No explanations, no markdown, no text before or after the JSON.
        """
    )
    # print("RAW RESPONSE:", response.text)  # debug
    
    text = response.text.strip()
    if not text:
        return patient_ledger

    # more robust markdown stripping
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


def build_ledger(df):
    ledger_output = []

    for user_id, user_df in df.groupby("user_id"):
        patient_name = user_df["patient_name"].iloc[0]
        disease_groups = defaultdict(list)

        # sort chronologically
        user_df = user_df.sort_values("dose_date")

        for _, row in user_df.iterrows():
            vaccine_info = lookup_vaccine(row["vaccine_name"])
            if vaccine_info:
                for disease in vaccine_info["diseases_prevented"]:
                    disease_groups[disease].append({
                        "vaccine_name": row["vaccine_name"],
                        "dose_date": row["dose_date"]
                    })
            else:
                # unmapped — flag for Gemini fallback
                # can temporarily rely on LLM call for now
                disease_groups["UNMAPPED"].append({
                    "vaccine_name": row["vaccine_name"],
                    "dose_date": row["dose_date"]
                })

        # build ledger entries per disease
        ledger = []
        for disease, doses in disease_groups.items():
            labeled_doses = [
                {"dose_label": f"Dose {i+1}", "vaccine_name": d["vaccine_name"], "dose_date": d["dose_date"]}
                for i, d in enumerate(doses)
            ]
            ledger.append({
                "disease_name": disease,
                "doses_received": labeled_doses,
                "doses_completed_count": len(labeled_doses),
                "doses_expected_count": None,  # TODO: plug in requirements database
                "completion_status": "Unknown",  # TODO: compute once expected count is known
                "missing_doses": []
            })

        ledger_output.append({
            "user_id": user_id,
            "patient_name": patient_name,
            "generated_at": pd.Timestamp.utcnow().isoformat(),
            "ledger": ledger
        })
    
    final_output = check_compliance(ledger_output)
    return final_output

result = build_ledger(df)
with open('data/ledger_example.json', 'w') as file:
    json.dump(result, file, indent=2)
