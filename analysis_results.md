# Arogyam.ai - Project Analysis Report

## 🏥 Overview
**Arogyam.ai** is an advanced AI-integrated healthcare platform designed to bridge the gap between patients, doctors, and pharmacists. It provides a seamless ecosystem for medical consultation, diagnosis, prescription management, and medication fulfillment.

## 🏗️ Architecture
The project follows a classic **Flask (Python)** monolithic architecture with a **MySQL** database and real-time capabilities via **Socket.IO**. It distinguishes itself through deep integration with Large Language Models (LLMs) to provide specialist-level medical guidance and safety checks.

### 👥 User Roles
1.  **Patients**: Can search for doctors, consult with AI or human specialists, manage prescriptions, and order medications.
2.  **Doctors**: Manage their digital clinic, chat with patients, and use AI tools to draft safe prescriptions.
3.  **Pharmacists**: Receive and fulfill medication orders linked directly to digital prescriptions.

---

## 🚀 Core Features

### 1. AI Specialist Consultations
The standout feature is the **AI Specialist** module, which uses sophisticated prompting to simulate specific medical disciplines:
- **Specialized Reasoning**: Includes prompts for Neurologists, Cardiologists, Orthopedics, GPs, Pulmonologists, Dentists, Dermatologists, and Gynecologists.
- **Structured Output**: Every AI response follows a strict clinical protocol:
    - 🧾 Symptoms Summary
    - ❓ Targeted Follow-up Questions
    - 🧠 Possible Conditions (with confidence levels)
    - 🧪 Recommended Diagnostic Tests
    - 💊 General Suggestions & Red Flags
    - ⚠️ Professional Disclaimer

### 2. Intelligent Prescription System
- **AI Scribe**: Automatically drafts prescriptions based on patient-doctor chat history.
- **Safety Verifier**: An LLM-based system that checks for drug-drug interactions, contraindications based on diagnosis, and age-appropriateness before a prescription is finalized.

### 3. Patient Care & RAG
- **Medical RAG Pipeline**: Uses ChromaDB and Sentence Transformers to provide evidence-based answers from uploaded medical documents (PDFs).
- **Automated Reminders**: Generates medication schedules and meal-timing alerts from prescriptions.
- **Smart Diet Plans**: Automatically generates dietary advice tailored to the patient's diagnosis and medications.

### 4. Real-time Communication
- Integrated chat system using **Flask-SocketIO**, allowing patients to connect with doctors or AI specialists instantly.

---

## 🛠️ Technical Stack

| Layer | Technology |
| :--- | :--- |
| **Core Framework** | Python (Flask) |
| **Database** | MySQL (Relational), ChromaDB (Vector) |
| **Real-time** | Flask-SocketIO |
| **AI Models** | Groq (Llama 3), Mistral AI |
| **Document Processing** | PyPDF, Pillow |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla) |

---

## 📂 Project Structure
- `backend/app.py`: Main entry point containing routing logic for all three user roles.
- `backend/models.py`: Central hub for AI logic, specialist prompts, and RAG implementation.
- `backend/templates/`: 20+ HTML templates covering dashboards, chats, and registrations.
- `backend/static/`: CSS and JS assets.
- `docs/`: Extensive guides on prompting and project setup.

## 💡 Observations & Recommendations
- **Monolithic App**: `app.py` and `models.py` are quite large (2500+ and 1800+ lines respectively). As the project grows, splitting these into smaller modules (e.g., `routes/`, `services/`, `ai/`) would improve maintainability.
- **Security**: The pharmacist login uses a license number as a unique identifier. Implementing a more robust authentication system (passwords/OTPs) would be safer.
- **AI Resilience**: The system has excellent fallback mechanisms in `models.py` for when AI APIs are unavailable, ensuring the platform remains functional.

---
*Analysis performed on 2026-04-18*
