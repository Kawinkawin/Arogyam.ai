# Arogyam Complete Product Requirements Document (All-in-One)

Date: 2026-04-11
Version: 1.0
Status: Draft baseline from current implementation

## 1. Document Purpose
This PRD combines all currently known product, workflow, architecture, API, model, and implementation details of Arogyam into one unified reference document.

## 2. Product Summary
Arogyam is a hybrid healthcare platform that provides:
- Human tele-consultation workflows between patients and doctors.
- Prescription authoring and medication safety assistance.
- Pharmacist order fulfillment and patient order tracking.
- AI-assisted specialist consultation (text, medical image analysis, and PDF report interpretation).

## 3. Product Vision
Provide fast, accessible, and clinically guided digital care with a unified flow from symptom consultation to prescription fulfillment, while supporting both human clinicians and AI specialist assistance.

## 4. Problem Statement
Users currently face fragmented care paths across consultation, diagnostics, and medication fulfillment. Arogyam addresses this by integrating:
- Specialist discovery
- Consultation
- Diagnostics support
- Prescription generation and checks
- Pharmacy fulfillment
in one platform.

## 5. Goals and Outcomes
Primary goals:
- Enable end-to-end patient care workflows in one product.
- Improve consultation speed using AI-assisted triage and analysis.
- Maintain role-specific experiences for patients, doctors, and pharmacists.

Business outcomes:
- Increased consultation completion rate.
- Faster prescription-to-order turnaround.
- Better specialist accessibility and routing.

Clinical outcomes:
- Structured specialist-style responses.
- Better medical image/report pre-analysis support.
- Improved medication safety awareness before final prescription confirmation.

## 6. Stakeholders and Personas
Primary personas:
- Patient: seeks consultation, guidance, prescription, and medicine fulfillment.
- Doctor: manages consultations, chats with patients, drafts and verifies prescriptions.
- Pharmacist: receives orders and updates fulfillment status.
- AI Specialist User: interacts with specialist AI for symptom and document/image analysis.

Internal stakeholders:
- Product owner
- Engineering team
- Clinical advisors
- Operations/support

## 7. In-Scope and Out-of-Scope
In scope:
- Web-based role portals and dashboards.
- Doctor-patient messaging and payment-gated consultation flow.
- Prescription creation, drafting support, medication safety checks.
- Pharmacy order creation and status management.
- AI specialist chat with file upload and analysis.
- Realtime signaling support for video call setup.

Out of scope for current release baseline:
- Native mobile apps.
- Full EHR interoperability standards integration.
- Insurance claims processing.
- Production-grade identity provider integration.

## 8. Current System Architecture

## 8.1 Runtime Architecture
- Single Flask application service handles all routes.
- Flask-SocketIO is used for signaling and emergency event push.
- MySQL is the persistent datastore.
- Flask-Session filesystem backend stores session state.
- Local filesystem stores uploaded analysis files and session files.
- External AI services:
  - Groq for text reasoning and prescription support.
  - Mistral Pixtral for vision analysis.

## 8.2 Technology Stack
- Python 3.x
- Flask
- Flask-SocketIO (threading mode)
- mysql-connector-python
- Flask-Session
- groq
- requests/httpx-compatible API call pattern
- pypdf
- sentence-transformers and chromadb dependencies present
- Jinja templates + CSS + inline JavaScript

## 8.3 Codebase Functional Structure
- backend/app.py: app wiring, routes, socket events, session and orchestration logic
- backend/models.py: AI clients and medical prompting logic
- backend/create_tables.py: schema creation script
- backend/reset_pharmacists.py: pharmacists table reset utility
- backend/templates/: page templates
- backend/static/css/: stylesheets
- backend/static/js/: currently empty
- uploads/: uploaded files
- flask_session/: server-side session files

## 9. User Workflows

## 9.1 Human Consultation Workflow
1. Patient signs up or logs in.
2. Patient selects doctor/specialist and opens consultation.
3. Payment is validated for consultation access.
4. Patient and doctor exchange messages.
5. Doctor creates prescription.
6. Prescription can be sent to pharmacist order flow.
7. Pharmacist updates order lifecycle.
8. Patient tracks order status.

## 9.2 AI Specialist Workflow
1. User opens AI specialists page and selects specialist.
2. User enters symptoms in specialist chat.
3. Optional file upload (PDF/image/DICOM).
4. Backend processes message and files:
   - text-only specialist response via Groq, or
   - report/image analysis plus specialist synthesis.
5. Structured response is returned.
6. Session is kept specialist-scoped.

## 9.3 Emergency Triage Workflow
1. AI message content is scanned for emergency keywords.
2. If matched, emergency triage event is emitted via SocketIO.
3. Doctor dashboard receives and displays alert.

## 9.4 Video Call Signaling Workflow
1. Client joins room identified by doctor_id_patient_id.
2. Caller emits start_call.
3. Offer/answer/candidate events are relayed by server.
4. Peer-to-peer WebRTC media path is established by clients.

Current limitation:
- Full WebRTC flow is implemented in doctor-side chat_with_patient page.
- Patient-side chat_doctor page has call icons but no full signaling implementation.

## 10. Functional Requirements

## 10.1 Core Platform and Authentication
- FR-001: System shall support patient registration and login.
- FR-002: System shall support doctor registration and login.
- FR-003: System shall support pharmacist registration and login.
- FR-004: System shall support role-specific dashboards.
- FR-005: System shall provide logout that clears session.

## 10.2 Consultation and Messaging
- FR-006: System shall support patient-doctor chat sessions.
- FR-007: System shall persist messages with sender and timestamp.
- FR-008: System shall provide message retrieval endpoint for conversation history.
- FR-009: System shall enforce payment gate before paid consultation access.

## 10.3 Prescription and Medication Safety
- FR-010: Doctor shall be able to create prescription with diagnosis and medicines.
- FR-011: System shall store prescription and medicine line items.
- FR-012: System shall provide AI prescription drafting from recent chat.
- FR-013: System shall provide AI medication safety verification endpoint.

## 10.4 Pharmacy and Fulfillment
- FR-014: Patient shall be able to discover pharmacists.
- FR-015: Patient shall be able to create an order from prescription.
- FR-016: Pharmacist shall be able to update order status.
- FR-017: Patient shall be able to view order history and status progression.

## 10.5 AI Specialist Consultation
- FR-018: System shall provide specialist selection and specialist chat page.
- FR-019: System shall generate structured specialist responses.
- FR-020: System shall support specialist-specific prompt behavior.
- FR-021: System shall support follow-up context across conversation turns.

## 10.6 File Upload and Analysis
- FR-022: System shall accept PDF, PNG, JPG, JPEG, and DICOM uploads.
- FR-023: System shall validate file type and size before processing.
- FR-024: System shall process PDFs for RAG-style snippet answering.
- FR-025: System shall process images with modality-aware vision analysis.
- FR-026: System shall blend image/report findings into specialist chat response.

## 10.7 Session Isolation and Lifecycle
- FR-027: AI session context shall be isolated by specialist type.
- FR-028: System shall support session clear endpoint removing uploaded files and pipeline state.
- FR-029: Legacy shared session keys shall be removed to prevent cross-specialist leakage.

## 10.8 Realtime and Video Signaling
- FR-030: System shall expose SocketIO signaling events for WebRTC negotiation.
- FR-031: System shall support emergency triage realtime event delivery.
- FR-032: System shall provide symmetric signaling support across patient and doctor chat UIs.

## 11. Non-Functional Requirements
- NFR-001: Availability target for primary app routes during operating hours.
- NFR-002: P95 API response time for standard text chat should remain acceptable under moderate load.
- NFR-003: Upload and AI calls should handle transient external failures with clear user-facing fallback.
- NFR-004: Data integrity must be preserved for prescriptions and orders.
- NFR-005: Input validation and secure handling for all user-supplied form/API data.
- NFR-006: Session isolation must prevent data leakage between specialist consultations.
- NFR-007: Auditability through server logs for major workflow steps and failures.

## 12. Data Model and Persistence

## 12.1 Core Tables
- patients
- doctors
- chats
- payments
- prescriptions
- prescription_medicines
- pharmacists
- orders

## 12.2 Key Relationships
- patient and doctor to chats
- doctor and patient to payments
- doctor and patient to prescriptions
- prescription to prescription_medicines
- prescription, pharmacist, and patient to orders

## 12.3 Data Lifecycle
- Chats and prescriptions remain persistent in MySQL.
- Uploaded files persist in uploads until clear-session cleanup.
- Specialist AI context persists in server session storage.

## 13. API and Realtime Inventory

## 13.1 HTTP Routes
| Method(s) | Route | Purpose |
|---|---|---|
| GET | / | Render main landing page |
| GET | /debug/check-tables | Verify key DB tables exist |
| GET | /doctor | Doctor consultation entry page |
| GET | /patient | Patient portal entry page |
| GET | /pharmacist | Pharmacist registration page |
| POST | /register_pharmacist | Register pharmacist profile |
| GET | /pharmacist_dashboard/<int:pharmacist_id> | Pharmacist dashboard with orders |
| POST | /update_pharmacist/<int:pharmacist_id> | Update pharmacist profile |
| GET, POST | /pharmacist_login | Pharmacist login flow |
| GET | /logout | Clear session and redirect home |
| GET | /ai | Redirect to specialist AI page |
| GET | /loginpatient | Render patient login page |
| GET | /patient_dashboard | Render patient dashboard with specialists |
| GET, POST | /submit | Patient signup |
| GET | /login | Render patient registered login page |
| GET | /pl | Render patient login template |
| GET, POST | /pmain | Validate patient credentials |
| GET | /specialist/<specialization> | List doctors by specialization |
| GET | /logindoctor | Redirect to doctor login |
| GET | /doctor_dashboard | Doctor dashboard with patient chat list |
| GET, POST | /doctor_signup | Doctor registration |
| GET, POST | /doctor_login | Doctor login |
| GET | /chat/<int:doctor_id>/<int:patient_id> | Patient-to-doctor chat page |
| POST | /pay/<int:doctor_id>/<int:patient_id> | Mark consultation payment as paid |
| POST | /send_message | Insert chat message |
| GET | /get_messages/<int:doctor_id>/<int:patient_id> | Retrieve conversation messages |
| GET | /chat_with_patient/<int:doctor_id>/<int:patient_id> | Doctor-side chat view for a patient |
| GET | /give_prescription/<int:doctor_id>/<int:patient_id> | Open prescription drafting page |
| POST | /save_prescription | Save prescription and medicines |
| GET | /api/draft_prescription/<int:doctor_id>/<int:patient_id> | AI prescription draft from chat |
| POST | /api/verify_prescription | AI medication safety check |
| GET | /get_prescriptions/<int:patient_id> | Fetch patient prescriptions |
| GET | /view_prescriptions/<int:doctor_id>/<int:patient_id> | View prescriptions UI |
| GET | /api/get_pharmacists | List pharmacists |
| POST | /api/create_order | Create pharmacy order |
| POST | /api/update_order_status | Update order status |
| GET | /patient_orders/<int:patient_id> | Patient order tracking page |
| GET | /index | Render AI landing index page |
| GET | /specialists | Render specialist selection page |
| GET | /chat/<specialist_type> | Render AI specialist chat page |
| POST | /api/chat | AI chat processing endpoint |
| POST | /api/upload | AI file upload endpoint |
| POST | /api/clear-session | Clear AI session and uploaded files |
| POST | /api/patient-info | Save patient metadata into session |

## 13.2 SocketIO Events
| Event | Direction | Purpose |
|---|---|---|
| join_room | client -> server | Join doctor/patient signaling room |
| start_call | client -> server | Notify peer of incoming call |
| webrtc_offer | client -> server -> peer | Relay WebRTC offer SDP |
| webrtc_answer | client -> server -> peer | Relay WebRTC answer SDP |
| webrtc_ice_candidate | client -> server -> peer | Relay ICE candidates |
| connect | socket lifecycle | Log socket connection |
| disconnect | socket lifecycle | Log socket disconnection |

## 14. AI and Medical Model Strategy

## 14.1 Current AI Components
- Text reasoning and structured specialist response: GroqChatClient
- Vision analysis with modality prompts: VisionModelClient using Pixtral
- PDF extraction and snippet retrieval: MedicalRAGPipeline

## 14.2 Current Specialist Coverage
- general_practitioner
- cardiologist
- dermatologist
- orthopedic
- gynecologist
- neurologist
- pulmonologist
- dentist

## 14.3 Specialist Coverage Gaps Identified
- Gynecologist is present in backend specialist config but missing in key frontend listings and doctor signup options.
- Additional specialist categories recommended for future expansion.

## 14.4 Additional Specialist Names Recommended
- Endocrinologist
- Pediatrician
- Psychiatrist
- Gastroenterologist
- Nephrologist
- Urologist
- Oncologist
- Ophthalmologist
- ENT (Otolaryngologist)
- Rheumatologist
- Hematologist
- Infectious Disease Specialist

## 14.5 Recommended Medical Model Names
Text/clinical model names:
- Llama-3.3-70B-Instruct
- Meditron-70B
- Qwen2.5-72B-Instruct
- ClinicalCamel-70B

Vision/multimodal model names:
- Pixtral-12B-2409
- Qwen2.5-VL-72B-Instruct
- Llama-3.2-90B-Vision-Instruct
- Gemini-2.5-Pro-Vision

Suggested specialist to model naming map:
- Cardiologist -> Meditron-70B + Qwen2.5-VL-72B-Instruct
- Neurologist -> Llama-3.3-70B-Instruct + Qwen2.5-VL-72B-Instruct
- Orthopedic -> Llama-3.3-70B-Instruct + Pixtral-12B-2409
- Pulmonologist -> Meditron-70B + Pixtral-12B-2409
- Dermatologist -> ClinicalCamel-70B + Qwen2.5-VL-72B-Instruct
- Gynecologist -> Llama-3.3-70B-Instruct + Qwen2.5-VL-72B-Instruct
- Dentist -> Llama-3.3-70B-Instruct + Pixtral-12B-2409
- General Practitioner -> Qwen2.5-72B-Instruct + Pixtral-12B-2409
- Endocrinologist -> Meditron-70B
- Pediatrician -> Llama-3.3-70B-Instruct
- Psychiatrist -> Qwen2.5-72B-Instruct
- Gastroenterologist -> Meditron-70B
- Nephrologist -> Meditron-70B
- Urologist -> Meditron-70B
- Oncologist -> Meditron-70B + Qwen2.5-VL-72B-Instruct
- Ophthalmologist -> Llama-3.2-90B-Vision-Instruct
- ENT (Otolaryngologist) -> Llama-3.3-70B-Instruct
- Rheumatologist -> Meditron-70B
- Hematologist -> Meditron-70B
- Infectious Disease Specialist -> Qwen2.5-72B-Instruct

## 15. Safety, Security, and Compliance Considerations
Current strengths:
- Input validation exists on multiple routes.
- Allowed upload extension list and max file size are configured.
- Specialist-scoped AI session isolation is implemented.

Current risks:
- Patient and doctor passwords are currently plain text in DB flows.
- SQL calls are direct in route handlers and need stronger central controls.
- Inline JavaScript duplication creates maintainability and drift risk.
- Video call implementation is asymmetric between user roles.

Required hardening direction:
- Password hashing and stronger authentication lifecycle.
- Centralized configuration and secrets handling.
- Stronger endpoint-level authorization checks.
- Centralized service layer for DB and AI calls.

## 16. Environment and Configuration Requirements
Environment keys used:
- FLASK_SECRET_KEY
- DB_HOST
- DB_USER
- DB_PASSWORD
- DB_NAME
- GROQ_API_KEY
- GROQ_MODEL
- MISTRAL_API_KEY

Operational constraints:
- AI performance and reliability depend on third-party model API availability.
- Upload performance depends on file size and external inference latency.

## 17. Known Gaps and Prioritized Backlog
High priority:
1. Fix socket runtime startup consistency.
2. Fix template signaling variable parity and WebRTC symmetry.
3. Harden app configuration routing and environment handling.
4. Align schema scripts and runtime assumptions.
5. Stabilize model client interfaces and response contracts.
6. Run validation and regression checks across all critical flows.

Medium priority:
1. Add missing specialist parity in all user-facing pages.
2. Move inline JS logic into reusable static modules.
3. Move polling chat to socket-based message streaming.
4. Add migration/versioning approach for DB evolution.

## 18. Acceptance Criteria
Product-level acceptance criteria:
- AC-001: Patient-doctor chat works end-to-end with persisted messages.
- AC-002: Prescription can be created, stored, viewed, and ordered.
- AC-003: Pharmacist can update order statuses and patient can track them.
- AC-004: AI specialist chat supports text-only and file-assisted analysis.
- AC-005: Specialist session context is isolated and clear-session cleanup works.
- AC-006: Emergency triage alerts emit and display correctly.
- AC-007: Video call signaling is fully usable from both patient and doctor sides.
- AC-008: Core routes and APIs pass validation/error checks.

## 19. QA and Validation Plan
Test categories:
- Unit checks for model client input/output handling.
- Integration checks for route to DB and route to AI chains.
- End-to-end smoke tests for:
  - signup/login per role
  - consultation chat and payment gating
  - prescription draft/verify/save
  - pharmacy order lifecycle
  - AI chat with upload and analysis
  - emergency triage event display
  - video call signaling parity

Operational checks:
- Startup sanity checks for env configuration.
- DB table verification route and schema consistency checks.
- Upload and cleanup lifecycle checks.

## 20. Release and Rollout Plan
Phase 1:
- Stabilize critical runtime and signaling parity.
- Validate all existing human and AI workflows.

Phase 2:
- Security hardening and config refactor.
- Specialist UI parity and model interface stabilization.

Phase 3:
- Advanced optimization and modularization.
- Expanded specialist catalog and richer triage/model routing.

## 21. Metrics and KPIs
Suggested measurable metrics:
- Consultation completion rate.
- Average time from consultation to prescription save.
- Average time from prescription to order creation.
- AI response success rate and fallback rate.
- Upload-to-analysis success rate.
- Emergency triage alert accuracy review rate.
- Video call setup success rate between both parties.

## 22. Open Questions
- Should room identifiers remain doctor_id/patient_id or support phone/identity-based signaling mapping?
- What is the required security compliance baseline for production launch?
- Should RAG remain lightweight in-memory or move to persistent vector storage in production?
- What specialist expansion sequence is clinically and operationally preferred?

## 23. Definitions
- PRD: Product Requirements Document.
- RAG: Retrieval-Augmented Generation.
- SDP: Session Description Protocol used in WebRTC signaling.
- ICE: Interactive Connectivity Establishment candidates for peer connectivity.

## 24. Final Summary
Arogyam already implements a broad and functional hybrid care platform. This all-in-one PRD captures the full known state of architecture, workflows, APIs, models, risks, and delivery priorities in one master document suitable for product, engineering, and planning alignment.
