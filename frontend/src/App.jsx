import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [problem, setProblem] = useState("");
  const [investigation, setInvestigation] = useState(null);

  const [document, setDocument] = useState(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [documentError, setDocumentError] = useState("");

  const [loading, setLoading] = useState(false);

  // ---------------------------------------
  // Maintenance records
  // ---------------------------------------
  const [maintenanceRecords, setMaintenanceRecords] = useState([]);
  const [showMaintenanceForm, setShowMaintenanceForm] = useState(false);
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  const [maintenanceError, setMaintenanceError] = useState("");
  const [maintenanceForm, setMaintenanceForm] = useState({
    date: "",
    equipment_id: "",
    issue: "",
    action: "",
    result: "",
  });

  const loadMaintenanceRecords = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/maintenance-records"
      );

      if (!response.ok) {
        throw new Error("Could not load maintenance records.");
      }

      const data = await response.json();
      setMaintenanceRecords(data.records || []);
    } catch (error) {
      console.error(error);
      setMaintenanceError(
        "Could not load maintenance history. Make sure the FastAPI server is running."
      );
    }
  };

  useEffect(() => {
    loadMaintenanceRecords();
  }, []);

  const addMaintenanceRecord = async (event) => {
    event.preventDefault();

    if (
      !maintenanceForm.date ||
      !maintenanceForm.equipment_id.trim() ||
      !maintenanceForm.issue.trim() ||
      !maintenanceForm.action.trim() ||
      !maintenanceForm.result.trim()
    ) {
      setMaintenanceError("Please complete all maintenance record fields.");
      return;
    }

    setMaintenanceLoading(true);
    setMaintenanceError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/maintenance-record",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(maintenanceForm),
        }
      );

      if (!response.ok) {
        throw new Error("Could not save maintenance record.");
      }

      const data = await response.json();

      setMaintenanceRecords((current) => [
        ...current,
        data.record,
      ]);

      setMaintenanceForm({
        date: "",
        equipment_id: "",
        issue: "",
        action: "",
        result: "",
      });

      setShowMaintenanceForm(false);
    } catch (error) {
      console.error(error);
      setMaintenanceError(
        "IMIA could not save the maintenance record. Check the backend server."
      );
    } finally {
      setMaintenanceLoading(false);
    }
  };

  // ---------------------------------------
  // Upload technical document
  // ---------------------------------------
  const uploadDocument = async (event) => {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      setDocumentError("Please upload a PDF document.");
      return;
    }

    setDocumentLoading(true);
    setDocumentError("");
    setDocument(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        "http://127.0.0.1:8000/upload-document",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Document upload failed.");
      }

      const data = await response.json();

      console.log("IMIA DOCUMENT RESPONSE:", data);

      setDocument(data);
    } catch (error) {
      console.error(error);

      setDocumentError(
        "IMIA could not read the document. Make sure the FastAPI server is running."
      );
    } finally {
      setDocumentLoading(false);
    }
  };

  // ---------------------------------------
  // Start AI investigation
  // ---------------------------------------
  const startInvestigation = async () => {
    if (!problem.trim()) {
      alert("Please describe the equipment problem first.");
      return;
    }

    setLoading(true);
    setInvestigation(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/investigate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            problem: problem,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Backend request failed.");
      }

      const data = await response.json();

      console.log("IMIA RESPONSE:", data);

      setInvestigation(data);
    } catch (error) {
      console.error(error);

      setInvestigation({
        status: "error",
        message:
          "IMIA could not connect to the backend. Make sure the FastAPI server is running.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">

      {/* ---------------------------------------
          TOP BAR
      --------------------------------------- */}
      <header className="topbar">
        <div>
          <h1>IMIA</h1>

          <span>
            Industrial Maintenance Intelligence Agent
          </span>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          System Online
        </div>
      </header>


      {/* ---------------------------------------
          MAIN DASHBOARD
      --------------------------------------- */}
      <main className="dashboard">

        {/* SIDEBAR */}
        <aside className="sidebar">

          <button className="new-case">
            + New Investigation
          </button>

          <nav>
            <div className="nav-section">
              WORKSPACE
            </div>

            <a className="active">
              Investigation
            </a>

            <a>
              Evidence
            </a>

            <a>
              Maintenance History
            </a>
          </nav>

          <div className="sidebar-bottom">

            <div className="nav-section">
              SYSTEM
            </div>

            <a>
              Settings
            </a>

          </div>

        </aside>


        {/* WORKSPACE */}
        <section className="workspace">

          <div className="workspace-header">

            <div>

              <p className="eyebrow">
                MAINTENANCE INVESTIGATION
              </p>

              <h2>
                What is happening with the equipment?
              </h2>

              <p className="subtitle">
                Describe the problem and provide any available
                maintenance evidence.
              </p>

            </div>

          </div>


          {/* ---------------------------------------
              INVESTIGATION CARD
          --------------------------------------- */}
          <div className="investigation-card">

            <label htmlFor="problem">
              Problem description
            </label>

            <textarea
              id="problem"
              value={problem}
              onChange={(event) =>
                setProblem(event.target.value)
              }
              placeholder="Example: The motor shuts down after running for approximately 10 minutes..."
            />


            {/* ---------------------------------------
                EVIDENCE UPLOADS
            --------------------------------------- */}
            <div className="evidence-row">


              {/* TECHNICAL DOCUMENTS */}
              <div className="evidence-card">

                <div className="evidence-icon">
                  📄
                </div>

                <div>
                  <strong>
                    Technical Documents
                  </strong>

                  <p>
                    Manuals, procedures, specifications
                  </p>

                  {document && (
                    <small>
                      ✓ {document.filename}
                    </small>
                  )}

                </div>

                <label className="upload-button">

                  {documentLoading
                    ? "Reading..."
                    : "Upload"}

                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={uploadDocument}
                    hidden
                  />

                </label>

              </div>


              {/* EQUIPMENT IMAGES */}
              <div className="evidence-card">

                <div className="evidence-icon">
                  🖼️
                </div>

                <div>
                  <strong>
                    Equipment Images
                  </strong>

                  <p>
                    Photos, diagrams, visual evidence
                  </p>
                </div>

                <button>
                  Upload
                </button>

              </div>


              {/* MAINTENANCE RECORDS */}
              <div className="evidence-card">

                <div className="evidence-icon">
                  📋
                </div>

                <div>
                  <strong>
                    Maintenance Records
                  </strong>

                  <p>
                    Error logs, history, service records
                  </p>
                </div>

                <button>
                  Upload
                </button>

              </div>

            </div>


            {/* ---------------------------------------
                MAINTENANCE RECORDS
            --------------------------------------- */}
            <div className="maintenance-manager">

              <div className="maintenance-manager-header">
                <div>
                  <strong>Maintenance Records</strong>
                  <p>
                    Add previous service events, fault history, and technician actions.
                  </p>
                </div>

                <button
                  type="button"
                  className="maintenance-toggle"
                  onClick={() => setShowMaintenanceForm((current) => !current)}
                >
                  {showMaintenanceForm ? "Cancel" : "+ Add Record"}
                </button>
              </div>

              {maintenanceError && (
                <div className="maintenance-error">
                  {maintenanceError}
                </div>
              )}

              {showMaintenanceForm && (
                <form
                  className="maintenance-form"
                  onSubmit={addMaintenanceRecord}
                >
                  <div className="maintenance-form-grid">
                    <label>
                      Date
                      <input
                        type="date"
                        value={maintenanceForm.date}
                        onChange={(event) =>
                          setMaintenanceForm({
                            ...maintenanceForm,
                            date: event.target.value,
                          })
                        }
                      />
                    </label>

                    <label>
                      Equipment ID
                      <input
                        type="text"
                        placeholder="MTR-204"
                        value={maintenanceForm.equipment_id}
                        onChange={(event) =>
                          setMaintenanceForm({
                            ...maintenanceForm,
                            equipment_id: event.target.value,
                          })
                        }
                      />
                    </label>

                    <label className="maintenance-form-wide">
                      Issue
                      <input
                        type="text"
                        placeholder="Motor shutdown during operation"
                        value={maintenanceForm.issue}
                        onChange={(event) =>
                          setMaintenanceForm({
                            ...maintenanceForm,
                            issue: event.target.value,
                          })
                        }
                      />
                    </label>

                    <label className="maintenance-form-wide">
                      Action Taken
                      <input
                        type="text"
                        placeholder="Checked VFD fault history"
                        value={maintenanceForm.action}
                        onChange={(event) =>
                          setMaintenanceForm({
                            ...maintenanceForm,
                            action: event.target.value,
                          })
                        }
                      />
                    </label>

                    <label className="maintenance-form-wide">
                      Result
                      <input
                        type="text"
                        placeholder="OVERLOAD fault recorded"
                        value={maintenanceForm.result}
                        onChange={(event) =>
                          setMaintenanceForm({
                            ...maintenanceForm,
                            result: event.target.value,
                          })
                        }
                      />
                    </label>
                  </div>

                  <button
                    type="submit"
                    className="maintenance-save"
                    disabled={maintenanceLoading}
                  >
                    {maintenanceLoading ? "Saving..." : "Save Maintenance Record"}
                  </button>
                </form>
              )}

              {maintenanceRecords.length > 0 && (
                <div className="maintenance-record-list">
                  {maintenanceRecords.map((record) => (
                    <div
                      key={record.record_id}
                      id={`maintenance-${record.record_id}`}
                      className="maintenance-record"
                    >
                      <div className="maintenance-record-header">
                        <strong>{record.record_id}</strong>
                        <span>{record.date}</span>
                      </div>
                      <div className="maintenance-record-equipment">
                        Equipment: {record.equipment_id}
                      </div>
                      <p><strong>Issue:</strong> {record.issue}</p>
                      <p><strong>Action:</strong> {record.action}</p>
                      <p><strong>Result:</strong> {record.result}</p>
                    </div>
                  ))}
                </div>
              )}

            </div>


            {/* DOCUMENT ERROR */}
            {documentError && (
              <div className="document-error">
                {documentError}
              </div>
            )}


            {/* ---------------------------------------
                START INVESTIGATION
            --------------------------------------- */}
            <button
              className="investigate-button"
              onClick={startInvestigation}
              disabled={loading}
            >
              {loading
                ? "Investigating..."
                : "Start Investigation →"}
            </button>

          </div>


          {/* ---------------------------------------
              DOCUMENT EVIDENCE PREVIEW
          --------------------------------------- */}
          {document && (
            <div className="result-card">

              <span className="preview-label">
                DOCUMENT EVIDENCE
              </span>

              <h3>
                {document.filename}
              </h3>

              <div className="problem-result">

                <strong>
                  Document successfully read
                </strong>

                <p>
                  Pages: {document.pages}
                </p>

              </div>


              <div className="ai-analysis">

                <strong>
                  Extracted Text Preview
                </strong>

                <pre>
                  {document.text.slice(0, 5000)}
                </pre>

              </div>

            </div>
          )}


          {/* ---------------------------------------
              AI INVESTIGATION RESULT
          --------------------------------------- */}
          {investigation && (
            <div className="result-card">

              <span className="preview-label">
                INVESTIGATION RESULT
              </span>

              <h3>
                {investigation.status === "error"
                  ? "Connection Error"
                  : "Investigation Received"}
              </h3>


              {investigation.message && (
                <p>
                  {investigation.message}
                </p>
              )}


              {investigation.investigation && (
  <div className="ai-analysis">

    <strong>
      IMIA Investigation
    </strong>

    {/* ---------------------------------------
        PROBLEM SUMMARY
    --------------------------------------- */}
    <div className="investigation-summary">

      <h4>Reported Problem</h4>

      <p>
        {investigation.investigation.investigation}
      </p>

    </div>


    {/* ---------------------------------------
        POTENTIAL CAUSES
    --------------------------------------- */}
    {investigation.investigation.potential_causes &&
      investigation.investigation.potential_causes.length > 0 && (

        <div className="potential-causes">

          <h4>Potential Causes</h4>

          {investigation.investigation.potential_causes.map(
            (cause, index) => (

              <div
                className="cause-card"
                key={index}
              >

                <div className="cause-header">

                  <span className="cause-number">
                    {index + 1}
                  </span>

                  <h3>
                    {cause.cause}
                  </h3>

                </div>


                {/* Why possible */}

                <div className="cause-section">

                  <strong>
                    Why it is possible
                  </strong>

                  <p>
                    {cause.why_possible}
                  </p>

                </div>


                {/* Evidence IDs */}

                {cause.evidence_ids &&
                  cause.evidence_ids.length > 0 && (

                    <div className="cause-section">

                      <strong>
                        Supporting Evidence
                      </strong>

                      <div className="evidence-id-list">

                        {cause.evidence_ids.map(
                          (evidenceId) => (

                            <button
                              type="button"
                              key={evidenceId}
                              className="evidence-id"
                              style={{ marginRight: "8px", marginBottom: "8px" }}
                              onClick={(event) => {
                                event.preventDefault();

                                const evidenceElement = window.document.getElementById(
                                  `evidence-${evidenceId}`
                                );

                                if (evidenceElement) {
                                  evidenceElement.scrollIntoView({
                                    behavior: "smooth",
                                    block: "center",
                                  });
                                }
                              }}
                            >
                              {evidenceId}
                            </button>

                          )
                        )}

                      </div>

                    </div>

                  )}


                {/* Maintenance History */}

                {cause.maintenance_record_ids &&
                  cause.maintenance_record_ids.length > 0 && (

                    <div className="cause-section">

                      <strong>
                        Maintenance History
                      </strong>

                      <div className="evidence-id-list">

                        {cause.maintenance_record_ids.map(
                          (recordId) => (

                            <button
                              type="button"
                              key={recordId}
                              className="evidence-id"
                              style={{ marginRight: "8px", marginBottom: "8px" }}
                              onClick={(event) => {
                                event.preventDefault();

                                const recordElement = window.document.getElementById(
                                  `maintenance-${recordId}`
                                );

                                if (recordElement) {
                                  recordElement.scrollIntoView({
                                    behavior: "smooth",
                                    block: "center",
                                  });
                                }
                              }}
                            >
                              {recordId}
                            </button>

                          )
                        )}

                      </div>

                    </div>

                  )}


                {/* Technician check */}

                <div className="cause-section">

                  <strong>
                    Technician Check
                  </strong>

                  <p>
                    {cause.technician_check}
                  </p>

                </div>

              </div>

            )
          )}

        </div>

      )}


    {/* ---------------------------------------
        EVIDENCE SUMMARY
    --------------------------------------- */}
    {investigation.investigation.evidence_summary &&
      investigation.investigation.evidence_summary.length > 0 && (

        <div className="evidence-summary">

          <h4>Evidence Summary</h4>

          {investigation.investigation.evidence_summary.map(
            (item, index) => (

              <div
                className="evidence-summary-card"
                key={index}
              >

                <div className="evidence-summary-header">

                  <strong>
                    {item.evidence_id}
                  </strong>

                </div>

                <p>
                  <strong>Finding:</strong>{" "}
                  {item.finding}
                </p>

                <p>
                  <strong>Why it matters:</strong>{" "}
                  {item.why_it_matters}
                </p>

              </div>

            )
          )}

        </div>

      )}


    {/* ---------------------------------------
        RECOMMENDED NEXT STEPS
    --------------------------------------- */}
    {investigation.investigation.recommended_next_steps &&
      investigation.investigation.recommended_next_steps.length > 0 && (

        <div className="next-steps">

          <h4>
            Recommended Next Steps
          </h4>

          <ol>

            {investigation.investigation.recommended_next_steps.map(
              (step, index) => (

                <li key={index}>
                  {step}
                </li>

              )
            )}

          </ol>

        </div>

      )}


    {/* ---------------------------------------
        INFORMATION GAPS
    --------------------------------------- */}
    {investigation.investigation.information_gaps &&
      investigation.investigation.information_gaps.length > 0 && (

        <div className="information-gaps">

          <h4>
            Information Gaps
          </h4>

          <ul>

            {investigation.investigation.information_gaps.map(
              (gap, index) => (

                <li key={index}>
                  {gap}
                </li>

              )
            )}

          </ul>

        </div>

      )}


    {/* ---------------------------------------
        MAINTENANCE HISTORY
    --------------------------------------- */}
    {investigation.retrieved_maintenance &&
      investigation.retrieved_maintenance.length > 0 && (

        <div className="evidence-section">

          <h4>
            Maintenance History
          </h4>

          <p className="evidence-intro">
            Historical maintenance records retrieved by IMIA
            are shown separately from technical documentation.
          </p>

          <div className="evidence-list">

            {investigation.retrieved_maintenance.map(
              (record) => (

                <div
                  key={record.record_id}
                  id={`maintenance-${record.record_id}`}
                  className="evidence-card"
                >

                  <div className="evidence-header">

                    <strong>
                      {record.record_id}
                    </strong>

                    <span>
                      {record.date}
                    </span>

                  </div>

                  <div className="evidence-document">
                    Equipment: {record.equipment_id}
                  </div>

                  <p>
                    <strong>Issue:</strong> {record.issue}
                  </p>

                  <p>
                    <strong>Action:</strong> {record.action}
                  </p>

                  <p>
                    <strong>Result:</strong> {record.result}
                  </p>

                </div>

              )
            )}

          </div>

        </div>

      )}


    {/* ---------------------------------------
        VERIFIED EVIDENCE
    --------------------------------------- */}
    {investigation.retrieved_evidence &&
      investigation.retrieved_evidence.length > 0 && (

        <div className="evidence-section">

          <h4>
            Verified Evidence
          </h4>

          <p className="evidence-intro">
            Evidence below was retrieved and verified
            by the IMIA backend. Page numbers and
            Evidence IDs come directly from the
            uploaded document.
          </p>


          <div className="evidence-list">

            {investigation.retrieved_evidence.map(
              (evidence) => (

                <div
                  key={evidence.evidence_id}
                  id={`evidence-${evidence.evidence_id}`}
                  className="evidence-card"
                >

                  <div className="evidence-header">

                    <strong>
                      {evidence.evidence_id}
                    </strong>

                    <span>
                      Page {evidence.page}
                    </span>

                  </div>


                  <div className="evidence-document">

                    {evidence.document}

                  </div>


                  <div className="evidence-text">

                    "{evidence.text}"

                  </div>


                  {evidence.matched_terms &&
                    evidence.matched_terms.length > 0 && (

                      <div className="matched-terms">

                        <strong>
                          Matched terms:
                        </strong>{" "}

                        {evidence.matched_terms.join(", ")}

                      </div>

                    )}

                </div>

              )
            )}

          </div>

        </div>

      )}

  </div>
)}


              {investigation.problem && (
                <div className="problem-result">

                  <strong>
                    Reported problem
                  </strong>

                  <p>
                    {investigation.problem}
                  </p>

                </div>
              )}

            </div>
          )}


          {/* ---------------------------------------
              FEATURE PREVIEW
          --------------------------------------- */}
          <div className="preview-grid">

            <div className="preview-card">

              <span className="preview-label">
                HYPOTHESES
              </span>

              <h3>
                Potential Causes
              </h3>

              <p>
                IMIA will generate and rank possible
                causes based on the available evidence.
              </p>

            </div>


            <div className="preview-card">

              <span className="preview-label">
                EVIDENCE
              </span>

              <h3>
                Show Me Why
              </h3>

              <p>
                Every recommendation will be connected
                to the evidence that supports it.
              </p>

            </div>


            <div className="preview-card">

              <span className="preview-label">
                ACTIONS
              </span>

              <h3>
                Next Steps
              </h3>

              <p>
                Receive practical troubleshooting checks
                based on the investigation.
              </p>

            </div>

          </div>

        </section>

      </main>

    </div>
  );
}

export default App;

