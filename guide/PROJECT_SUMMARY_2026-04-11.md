# Arogyam Project Summary
Date: 2026-04-11

## 1) Project Purpose
Arogyam is a hybrid healthcare platform with:
- Human tele-consultation (patient-doctor chat, prescriptions, pharmacist order flow)
- AI specialist consultation (text + medical image analysis + PDF report analysis)

## 2) Tech Stack
- Backend: Flask + Flask-SocketIO + MySQL
- AI: Groq text model + Mistral Pixtral vision model + lightweight PDF RAG
- Frontend: Server-rendered HTML templates with CSS and mostly inline JavaScript
- Sessions: Flask-Session (filesystem)

## 3) Frontend Summary
Main UI groups:
- Landing/AI flow: index.html -> specialist.html -> chat.html
- Human doctor flow: patient/doctor signup/login -> chat_doctor.html and chat_with_patient.html
- Prescription/order flow: prescription.html -> view_prescriptions.html -> pharmacist_dashboard.html -> patient_orders.html

Observation:
- backend/static/js is empty; most behavior is embedded inside templates.

## 4) Backend Summary
Core server file: backend/app.py
Major capabilities:
- Auth and dashboards for patients, doctors, pharmacists
- Chat persistence via chats table
- Prescription creation + AI drafting + AI safety verification
- Order creation and status updates for pharmacists
- AI specialist chat endpoint (/api/chat)
- File upload endpoint (/api/upload) for PDF/image/DICOM
- Session isolation by specialist to avoid context leakage
- WebRTC signaling handlers over SocketIO (join_room, start_call, offer/answer/candidate)

## 5) Database Summary
create_tables.py defines and creates:
- patients
- doctors
- prescriptions
- prescription_medicines
- pharmacists
- orders
- payments
- chats

These match the main app workflow and route usage.

## 6) AI Model Layer Summary
Core file: backend/models.py
Components:
- GroqChatClient
  - Structured clinical response format with follow-up questions and differential logic
  - Prescription drafting and medication safety checking
- VisionModelClient
  - Uses Mistral API (pixtral-12b-2409)
  - Modality-aware prompts (CT/MRI/X-ray/Ultrasound/generic)
  - Specialist-aware context for multiple specialties
- MedicalRAGPipeline
  - PDF text extraction with pypdf
  - Lightweight in-memory retrieval/snippet answers

## 7) Current Specialist Coverage
In backend specialist prompt/config logic:
- general_practitioner
- cardiologist
- dermatologist
- orthopedic
- gynecologist
- neurologist
- pulmonologist
- dentist

## 8) Coverage Gaps Found
1. Frontend specialist page does not list gynecologist.
2. Doctor signup specialization dropdown does not include gynecologist.
3. Patient-facing icon mapping in mainpatientpage has no explicit gynecologist icon branch.
4. Video call is not fully symmetric:
   - chat_with_patient.html includes WebRTC + SocketIO logic.
   - chat_doctor.html shows video/voice icons but has no WebRTC signaling handlers.
5. Current signaling uses doctor_id + patient_id room key, not phone-number pairing.

## 9) Missing Specialist Names To Add (names only)
Recommended additional specialist names:
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

## 10) Best Medical Model Names Per Specialist (names only)
Recommended text-clinical model names:
- Llama-3.3-70B-Instruct
- Meditron-70B
- Qwen2.5-72B-Instruct
- ClinicalCamel-70B

Recommended multimodal/vision model names:
- Pixtral-12B-2409
- Qwen2.5-VL-72B-Instruct
- Llama-3.2-90B-Vision-Instruct
- Gemini-2.5-Pro-Vision

Suggested specialist-to-model naming map:
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

## 11) Current Health Check
- Project has no active syntax/lint errors reported by editor diagnostics.
- Primary risk is feature parity between templates/routes (especially real-time video call path).
