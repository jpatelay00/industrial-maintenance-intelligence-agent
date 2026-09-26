from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
import ollama
import io
import re


app = FastAPI(
    title="Industrial Maintenance Intelligence Agent"
)


# ---------------------------------------
# CORS
# ---------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------
# Temporary document storage
# ---------------------------------------

uploaded_document = {
    "filename": None,
    "pages": [],
    "chunks": [],
}
# ---------------------------------------
# Temporary maintenance record storage
# ---------------------------------------

maintenance_records = []

# ---------------------------------------
# Request model
# ---------------------------------------

class InvestigationRequest(BaseModel):
    problem: str


class MaintenanceRecord(BaseModel):
    date: str
    equipment_id: str
    issue: str
    action: str
    result: str


# ---------------------------------------
# Health endpoints
# ---------------------------------------

@app.get("/")
def root():
    return {
        "name": "Industrial Maintenance Intelligence Agent",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }

# ---------------------------------------
# Maintenance Records
# ---------------------------------------

@app.post("/maintenance-record")
def add_maintenance_record(
    record: MaintenanceRecord
):

    record_id = (
        f"MR-{len(maintenance_records) + 1:03d}"
    )

    maintenance_record = {
        "record_id": record_id,
        "date": record.date,
        "equipment_id": record.equipment_id,
        "issue": record.issue,
        "action": record.action,
        "result": record.result,
    }

    maintenance_records.append(
        maintenance_record
    )

    return {
        "status": "success",
        "record": maintenance_record,
    }

@app.get("/maintenance-records")
def get_maintenance_records():

    return {
        "status": "success",
        "records": maintenance_records,
    }

# ---------------------------------------
# Create evidence chunks
# ---------------------------------------

def create_chunks(page_text, page_number, chunk_size=900):

    # Clean excessive whitespace
    cleaned_text = re.sub(
        r"\s+",
        " ",
        page_text
    ).strip()

    if not cleaned_text:
        return []

    chunks = []

    def add_chunk(text, chunk_type="general", title=None):
        text = text.strip()

        if not text:
            return

        # Remove isolated section numbers.
        text = re.sub(
            r"^\d+\.\s*",
            "",
            text
        ).strip()

        if not text:
            return

        chunks.append({
            "page": page_number,
            "text": text,
            "type": chunk_type,
            "title": title,
        })

    # -------------------------------------------------
    # 1. VFD FAULT REFERENCE
    # -------------------------------------------------

    vfd_section_match = re.search(
        r"(?:\d+\.\s*)?VFD Fault Reference",
        cleaned_text,
        flags=re.IGNORECASE
    )

    if vfd_section_match:

        # Content before VFD Fault Reference
        prefix = cleaned_text[
            :vfd_section_match.start()
        ].strip()

        if prefix:
            add_chunk(
                prefix,
                chunk_type="general"
            )

        # Everything after the VFD Fault Reference header
        vfd_text = cleaned_text[
            vfd_section_match.end():
        ].strip()

        # Stop at the next numbered section.
        next_section = re.search(
            r"\s+\d+\.\s+",
            vfd_text
        )

        if next_section:
            vfd_text = vfd_text[
                :next_section.start()
            ].strip()

        fault_names = [
            "OVERLOAD",
            "OVERTEMP",
            "OVERCURRENT",
            "UNDERVOLTAGE",
            "OVERVOLTAGE",
        ]

        fault_pattern = (
            r"\b("
            + "|".join(fault_names)
            + r")\b"
        )

        fault_matches = list(
            re.finditer(
                fault_pattern,
                vfd_text,
                flags=re.IGNORECASE
            )
        )

        for index, match in enumerate(fault_matches):

            fault_name = match.group(1).upper()

            start = match.start()

            if index + 1 < len(fault_matches):
                end = fault_matches[index + 1].start()
            else:
                end = len(vfd_text)

            fault_text = vfd_text[
                start:end
            ].strip()

            add_chunk(
                fault_text,
                chunk_type="fault",
                title=fault_name
            )

        # We don't need the general fallback after
        # successfully processing this section.
        return chunks

    # -------------------------------------------------
    # 2. MOTOR OVERHEATING TROUBLESHOOTING
    # -------------------------------------------------

    troubleshooting_match = re.search(
        r"(?:\d+\.\s*)?Troubleshooting\s*[—-]\s*Motor Overheating",
        cleaned_text,
        flags=re.IGNORECASE
    )

    if troubleshooting_match:

        prefix = cleaned_text[
            :troubleshooting_match.start()
        ].strip()

        if prefix:
            add_chunk(
                prefix,
                chunk_type="general"
            )

        troubleshooting_text = cleaned_text[
            troubleshooting_match.end():
        ].strip()

        # Remove table headings.
        troubleshooting_text = re.sub(
            r"^Possible Cause\s+Indication\s+Recommended Check\s*",
            "",
            troubleshooting_text,
            flags=re.IGNORECASE
        )

        causes = [
            "Restricted cooling airflow",
            "Excessive mechanical load",
            "Incorrect VFD settings",
            "Bearing problem",
        ]

        cause_pattern = (
            r"("
            + "|".join(
                re.escape(cause)
                for cause in causes
            )
            + r")"
        )

        cause_matches = list(
            re.finditer(
                cause_pattern,
                troubleshooting_text,
                flags=re.IGNORECASE
            )
        )

        for index, match in enumerate(cause_matches):

            title = match.group(1)

            start = match.start()

            if index + 1 < len(cause_matches):
                end = cause_matches[index + 1].start()
            else:
                end = len(troubleshooting_text)

            cause_text = troubleshooting_text[
                start:end
            ].strip()

            add_chunk(
                cause_text,
                chunk_type="troubleshooting",
                title=title
            )

        return chunks

    # -------------------------------------------------
    # 3. GENERAL-PURPOSE FALLBACK
    # -------------------------------------------------

    sentences = re.split(
        r"(?<=[.!?])\s+",
        cleaned_text
    )

    current_chunk = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        if re.fullmatch(
            r"\d+\.",
            sentence
        ):
            continue

        if (
            current_chunk
            and len(current_chunk) + len(sentence) > chunk_size
        ):
            add_chunk(
                current_chunk,
                chunk_type="general"
            )

            current_chunk = sentence

        else:

            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        add_chunk(
            current_chunk,
            chunk_type="general"
        )

    return chunks

# ---------------------------------------
# Upload technical document
# ---------------------------------------

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):

    global uploaded_document

    file_bytes = await file.read()

    pdf = PdfReader(
        io.BytesIO(file_bytes)
    )


    pages = []
    all_chunks = []


    # Extract each page
    for page_number, page in enumerate(
        pdf.pages,
        start=1
    ):

        page_text = page.extract_text() or ""

        pages.append({
            "page": page_number,
            "text": page_text,
        })


        # Create evidence chunks
        page_chunks = create_chunks(
            page_text,
            page_number
        )


        for chunk_number, chunk in enumerate(
            page_chunks,
            start=1
        ):

            chunk["chunk_id"] = (
                f"p{page_number}-c{chunk_number}"
            )

            all_chunks.append(chunk)


    # Store document and chunks
    uploaded_document = {
        "filename": file.filename,
        "pages": pages,
        "chunks": all_chunks,
    }


    # Preview text
    extracted_text = ""

    for page in pages:

        extracted_text += (
            f"\n--- PAGE {page['page']} ---\n"
        )

        extracted_text += page["text"]


    return {
        "status": "success",
        "filename": file.filename,
        "pages": len(pages),
        "chunks": len(all_chunks),
        "chunk_data": all_chunks,
        "text": extracted_text,
    }


# ---------------------------------------
# Retrieval Engine
# ---------------------------------------

def retrieve_relevant_evidence(
    problem,
    chunks,
    max_results=6
):

    # -----------------------------------
    # Extract words from problem
    # -----------------------------------

    problem_words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        problem.lower()
    )

    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "my",
        "our",
        "this",
        "that",
        "it",
        "and",
        "or",
        "to",
        "of",
        "for",
        "with",
        "on",
        "in",
        "after",
        "before",
        "about",
        "approximately",
        "running",
        "runs",
        "run",
        "when",
        "why",
        "what",
        "how",
    }

    keywords = [
        word
        for word in problem_words
        if word not in stop_words
        and len(word) > 2
    ]

    # -----------------------------------
    # Maintenance-related terms
    # -----------------------------------

    related_terms = {

        "shutdown": [
            "overload",
            "overtemp",
            "overcurrent",
            "fault",
            "thermal",
            "trip",
        ],

        "shuts": [
            "overload",
            "overtemp",
            "overcurrent",
            "fault",
            "thermal",
            "trip",
        ],

        "stops": [
            "overload",
            "overtemp",
            "overcurrent",
            "fault",
            "thermal",
            "trip",
        ],

        "hot": [
            "overheating",
            "temperature",
            "cooling",
            "fan",
            "airflow",
        ],

        "overheating": [
            "cooling",
            "airflow",
            "fan",
            "load",
            "bearing",
            "temperature",
        ],

        "motor": [
            "overheating",
            "cooling",
            "bearing",
            "load",
            "vfd",
        ],

        "vfd": [
            "overload",
            "overtemp",
            "overcurrent",
            "voltage",
            "frequency",
        ],
    }

    expanded_keywords = set(keywords)

    for keyword in keywords:

        if keyword in related_terms:

            expanded_keywords.update(
                related_terms[keyword]
            )

    # -----------------------------------
    # Score evidence chunks
    # -----------------------------------

    scored_chunks = []

    for chunk in chunks:

        chunk_text = chunk["text"]
        chunk_lower = chunk_text.lower()

        chunk_title = (
            chunk.get("title") or ""
        ).lower()

        chunk_type = (
            chunk.get("type") or "general"
        ).lower()

        score = 0

        matched_terms = []

        # -----------------------------------
        # Text matches
        # -----------------------------------

        for keyword in expanded_keywords:

            occurrences = chunk_lower.count(
                keyword.lower()
            )

            if occurrences > 0:

                score += min(
                    occurrences,
                    5
                )

                matched_terms.append(
                    keyword
                )

        # -----------------------------------
        # Title matches
        # -----------------------------------

        for keyword in expanded_keywords:

            if keyword.lower() in chunk_title:

                score += 4

                if keyword not in matched_terms:

                    matched_terms.append(
                        keyword
                    )

        # -----------------------------------
        # Chunk type bonuses
        # -----------------------------------

        if chunk_type == "troubleshooting":

            score += 2

        elif chunk_type == "fault":

            score += 2

        # -----------------------------------
        # Store scored evidence
        # -----------------------------------

        if score > 0:

            scored_chunks.append({

                "chunk_id": chunk["chunk_id"],

                "page": chunk["page"],

                "text": chunk["text"],

                "score": score,

                "matched_terms": matched_terms,

                "type": chunk_type,

                "title": chunk.get("title"),

            })

    # -----------------------------------
    # Rank strongest evidence first
    # -----------------------------------

    scored_chunks.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return scored_chunks[:max_results]

# ---------------------------------------
# Evidence Validation
# ---------------------------------------

def validate_evidence_references(
    structured_analysis,
    relevant_evidence
):

    # -----------------------------------
    # Build set of valid Evidence IDs
    # -----------------------------------

    valid_evidence_ids = {
        evidence["chunk_id"]
        for evidence in relevant_evidence
    }

    invalid_evidence_ids = []

    # -----------------------------------
    # Validate potential causes
    # -----------------------------------

    potential_causes = structured_analysis.get(
        "potential_causes",
        []
    )

    for cause in potential_causes:

        evidence_ids = cause.get(
            "evidence_ids",
            []
        )

        valid_ids = []

        for evidence_id in evidence_ids:

            if evidence_id in valid_evidence_ids:

                valid_ids.append(
                    evidence_id
                )

            else:

                invalid_evidence_ids.append(
                    evidence_id
                )

        cause["evidence_ids"] = valid_ids

    # -----------------------------------
    # Validate evidence summary
    # -----------------------------------

    evidence_summary = structured_analysis.get(
        "evidence_summary",
        []
    )

    validated_summary = []

    for evidence in evidence_summary:

        evidence_id = evidence.get(
            "evidence_id"
        )

        if evidence_id in valid_evidence_ids:

            validated_summary.append(
                evidence
            )

        else:

            if evidence_id:
                invalid_evidence_ids.append(
                    evidence_id
                )

    structured_analysis[
        "evidence_summary"
    ] = validated_summary

    # -----------------------------------
    # Remove duplicate invalid IDs
    # -----------------------------------

    invalid_evidence_ids = list(
        dict.fromkeys(
            invalid_evidence_ids
        )
    )

    # -----------------------------------
    # Validation result
    # -----------------------------------

    structured_analysis[
        "evidence_validation"
    ] = {

        "status": (
            "valid"
            if not invalid_evidence_ids
            else "corrected"
        ),

        "valid_evidence_ids": sorted(
            valid_evidence_ids
        ),

        "invalid_evidence_ids": (
            invalid_evidence_ids
        ),

    }

    return structured_analysis

# ---------------------------------------
# Maintenance Reference Validation
# ---------------------------------------

def validate_maintenance_references(
    structured_analysis,
    relevant_maintenance
):

    # -----------------------------------
    # Build set of valid Maintenance IDs
    # -----------------------------------

    valid_maintenance_ids = {
        record["record_id"]
        for record in relevant_maintenance
    }

    invalid_maintenance_ids = []

    # -----------------------------------
    # Validate potential causes
    # -----------------------------------

    potential_causes = structured_analysis.get(
        "potential_causes",
        []
    )

    for cause in potential_causes:

        maintenance_ids = cause.get(
            "maintenance_record_ids",
            []
        )

        valid_ids = []

        for maintenance_id in maintenance_ids:

            if maintenance_id in valid_maintenance_ids:

                valid_ids.append(
                    maintenance_id
                )

            else:

                invalid_maintenance_ids.append(
                    maintenance_id
                )

        cause["maintenance_record_ids"] = valid_ids

    # -----------------------------------
    # Remove duplicate invalid IDs
    # -----------------------------------

    invalid_maintenance_ids = list(
        dict.fromkeys(
            invalid_maintenance_ids
        )
    )

    # -----------------------------------
    # Validation result
    # -----------------------------------

    structured_analysis[
        "maintenance_validation"
    ] = {

        "status": (
            "valid"
            if not invalid_maintenance_ids
            else "corrected"
        ),

        "valid_maintenance_record_ids": sorted(
            valid_maintenance_ids
        ),

        "invalid_maintenance_record_ids": (
            invalid_maintenance_ids
        ),
    }

    return structured_analysis


# ---------------------------------------
# Deterministic maintenance linking
# ---------------------------------------

def normalize_reference_ids(ids, pattern):
    """Normalize model references into clean, unique ID lists."""
    if not isinstance(ids, list):
        return []

    normalized = []

    for value in ids:
        if not isinstance(value, str):
            continue

        matches = re.findall(pattern, value)

        if matches:
            normalized.extend(matches)
        else:
            cleaned = value.strip()
            if cleaned:
                normalized.append(cleaned)

    return list(dict.fromkeys(normalized))


def link_relevant_maintenance_records(
    structured_analysis,
    relevant_maintenance
):
    """Attach historically relevant maintenance records deterministically.

    The local model is allowed to suggest maintenance IDs, but the backend
    also checks the cause text against the actual retrieved maintenance
    record. This prevents the model from being the sole authority on the
    evidence relationship.
    """

    valid_records = {
        record["record_id"]: record
        for record in relevant_maintenance
    }

    for cause in structured_analysis.get("potential_causes", []):
        # First normalize any IDs returned by the model.
        model_ids = normalize_reference_ids(
            cause.get("maintenance_record_ids", []),
            r"MR-\d+"
        )
        model_ids = [
            value for value in model_ids
            if value in valid_records
        ]

        cause_text = " ".join([
            str(cause.get("cause", "")),
            str(cause.get("why_possible", "")),
            str(cause.get("technician_check", "")),
        ]).lower()

        linked_ids = list(dict.fromkeys(model_ids))

        # Deterministic matching against retrieved maintenance history.
        # Require at least two meaningful terms to reduce accidental links.
        for record_id, record in valid_records.items():
            record_text = " ".join([
                str(record.get("issue", "")),
                str(record.get("action", "")),
                str(record.get("result", "")),
            ]).lower()

            record_words = re.findall(r"\b[a-zA-Z0-9]+\b", record_text)
            meaningful_words = {
                word for word in record_words
                if len(word) > 3
                and word not in {
                    "with", "from", "that", "this", "during",
                    "after", "checked", "check", "recorded"
                }
            }

            matches = [
                word for word in meaningful_words
                if word in cause_text
            ]

            if len(set(matches)) >= 2:
                linked_ids.append(record_id)

        cause["maintenance_record_ids"] = list(dict.fromkeys(linked_ids))

    return structured_analysis


# ---------------------------------------
# AI Investigation
# ---------------------------------------

@app.post("/investigate")
def investigate(
    request: InvestigationRequest
):

    if not uploaded_document["chunks"]:

        return {
            "status": "error",
            "message": (
                "Please upload a technical document "
                "before starting the investigation."
            ),
        }


    # -----------------------------------
    # Retrieve technical evidence
    # -----------------------------------

    relevant_evidence = retrieve_relevant_evidence(
        request.problem,
        uploaded_document["chunks"]
    )


    # -----------------------------------
    # Retrieve maintenance history
    # -----------------------------------

    relevant_maintenance = []

    problem_lower = request.problem.lower()

    problem_words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        problem_lower
    )

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were",
        "has", "have", "had", "my", "our", "this",
        "that", "it", "and", "or", "to", "of", "for",
        "with", "on", "in", "after", "before",
        "about", "approximately", "running", "runs",
        "run", "when", "why", "what", "how"
    }

    keywords = [
        word
        for word in problem_words
        if word not in stop_words
        and len(word) > 2
    ]

    print("IMIA MAINTENANCE RECORDS:", maintenance_records)
    print("IMIA MAINTENANCE KEYWORDS:", keywords)

    for record in maintenance_records:

        record_text = (
            f"{record['equipment_id']} "
            f"{record['issue']} "
            f"{record['action']} "
            f"{record['result']}"
        ).lower()

        if any(
            keyword in record_text
            for keyword in keywords
        ):
            print(
                "IMIA MATCHED MAINTENANCE RECORD:",
                record
            )

            relevant_maintenance.append(record)


    # -----------------------------------
    # Build AI evidence context
    # -----------------------------------

    evidence_context = ""

    for evidence in relevant_evidence:

        evidence_context += f"""

[EVIDENCE ID: {evidence["chunk_id"]}]
[DOCUMENT: {uploaded_document["filename"]}]
[PAGE: {evidence["page"]}]

{evidence["text"]}

[/EVIDENCE]
"""


    if not relevant_evidence:

        evidence_context = """
No relevant evidence was found in the
uploaded document.
"""


    # -----------------------------------
    # Build maintenance history context
    # -----------------------------------

    maintenance_context = ""

    for record in relevant_maintenance:

        maintenance_context += f"""

[MAINTENANCE RECORD ID: {record["record_id"]}]
[DATE: {record["date"]}]
[EQUIPMENT ID: {record["equipment_id"]}]

ISSUE:
{record["issue"]}

ACTION TAKEN:
{record["action"]}

RESULT:
{record["result"]}

[/MAINTENANCE RECORD]
"""


    if not relevant_maintenance:

        maintenance_context = """
No relevant maintenance history was found.
"""


    # -----------------------------------
    # AI prompt
    # -----------------------------------

    prompt = f"""
You are IMIA, the Industrial Maintenance Intelligence Agent.

You help industrial maintenance technicians investigate
equipment problems using technical documentation and
maintenance history.

TECHNICIAN REPORT:

"{request.problem}"


RETRIEVED DOCUMENT EVIDENCE:

{evidence_context}


MAINTENANCE HISTORY:

{maintenance_context}


IMPORTANT RULES:

1. Only use the retrieved technical evidence as documented
technical evidence.

2. Do not invent evidence.

3. Do not invent page numbers.

4. Do not invent Evidence IDs.

5. Only reference Evidence IDs that appear in the
retrieved document evidence above.

6. You may make reasonable technical inferences, but
clearly distinguish them from documented evidence.

7. If the retrieved evidence does not support a claim,
say so.

8. A retrieved evidence chunk does NOT automatically
prove a diagnosis.

9. Maintenance records are historical records. They describe
what happened previously and must not be treated as technical
documentation.

10. Do not invent Maintenance Record IDs.

11. Only reference Maintenance Record IDs that appear in
the maintenance history above.

12. Clearly distinguish between technical documentation and
historical maintenance activity.

13. If a relevant maintenance record directly describes the
same equipment problem or a recorded fault, use its
Maintenance Record ID when explaining the possible cause.

14. Return ONLY valid JSON.

15. Do NOT use Markdown.

16. Do NOT include ```json or ``` around the response.


Return JSON using exactly this structure:

{{
  "investigation": "Brief summary of the technician's reported problem.",

  "potential_causes": [
    {{
      "cause": "Name of possible cause.",
      "why_possible": "Explain why the symptoms could be consistent with this cause.",

      "evidence_ids": [
        "Technical evidence ID supporting this possibility"
      ],

      "maintenance_record_ids": [
        "Maintenance Record ID supporting this possibility"
      ],

      "technician_check": "Practical troubleshooting check."
    }}
  ],

  "evidence_summary": [
    {{
      "evidence_id": "Evidence ID",
      "finding": "What the evidence says.",
      "why_it_matters": "Why this evidence matters."
    }}
  ],

  "recommended_next_steps": [
    "Practical troubleshooting step"
  ],

  "information_gaps": [
    "Additional information that would help narrow the diagnosis"
  ]
}}


REQUIREMENTS:

- Identify no more than 3 potential causes.
- Use only Evidence IDs provided in the retrieved evidence.
- Use only Maintenance Record IDs provided in the maintenance history.
- Maintenance Record IDs must only be placed in the
maintenance_record_ids field.
- Technical Evidence IDs must only be placed in the
evidence_ids field.
- Do not treat a maintenance record as proof that a technical
cause is currently present.
- If there is insufficient evidence for a cause, say so.
- Do not fabricate technical documentation.
- Keep the response concise and useful to a maintenance technician.
"""


    # -----------------------------------
    # Local AI
    # -----------------------------------

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )


    # -----------------------------------
    # Parse structured AI response
    # -----------------------------------

    import json

    ai_content = response["message"]["content"].strip()

    try:

        structured_analysis = json.loads(ai_content)

    except json.JSONDecodeError:

        structured_analysis = {
            "investigation": ai_content,
            "potential_causes": [],
            "evidence_summary": [],
            "recommended_next_steps": [],
            "information_gaps": [
                "The AI response could not be parsed into structured JSON."
            ],
        }


    # -----------------------------------
    # Normalize AI reference IDs before validation
    # -----------------------------------

    for cause in structured_analysis.get("potential_causes", []):
        cause["evidence_ids"] = normalize_reference_ids(
            cause.get("evidence_ids", []),
            r"p\d+-c\d+"
        )
        cause["maintenance_record_ids"] = normalize_reference_ids(
            cause.get("maintenance_record_ids", []),
            r"MR-\d+"
        )

    for item in structured_analysis.get("evidence_summary", []):
        item["evidence_id"] = normalize_reference_ids(
            [item.get("evidence_id", "")],
            r"p\d+-c\d+"
        )[0] if normalize_reference_ids(
            [item.get("evidence_id", "")],
            r"p\d+-c\d+"
        ) else item.get("evidence_id")

    # -----------------------------------
    # Validate AI Evidence References
    # -----------------------------------

    structured_analysis = validate_evidence_references(
        structured_analysis,
        relevant_evidence
    )


    # -----------------------------------
    # Link relevant maintenance history
    # -----------------------------------

    structured_analysis = link_relevant_maintenance_records(
        structured_analysis,
        relevant_maintenance
    )

    # -----------------------------------
    # Validate AI Maintenance References
    # -----------------------------------

    structured_analysis = validate_maintenance_references(
        structured_analysis,
        relevant_maintenance
    )


    # -----------------------------------
    # Return verified technical evidence
    # -----------------------------------

    verified_evidence = []

    for evidence in relevant_evidence:

        verified_evidence.append({
            "evidence_id": evidence["chunk_id"],
            "document": uploaded_document["filename"],
            "page": evidence["page"],
            "score": evidence["score"],
            "matched_terms": evidence["matched_terms"],
            "text": evidence["text"],
        })


    # -----------------------------------
    # Return verified maintenance history
    # -----------------------------------

    verified_maintenance = []

    for record in relevant_maintenance:

        verified_maintenance.append({
            "record_id": record["record_id"],
            "date": record["date"],
            "equipment_id": record["equipment_id"],
            "issue": record["issue"],
            "action": record["action"],
            "result": record["result"],
        })


    # -----------------------------------
    # Final response
    # -----------------------------------

    return {
        "status": "success",
        "problem": request.problem,
        "document": uploaded_document["filename"],
        "investigation": structured_analysis,
        "retrieved_evidence": verified_evidence,
        "retrieved_maintenance": verified_maintenance,
    }

