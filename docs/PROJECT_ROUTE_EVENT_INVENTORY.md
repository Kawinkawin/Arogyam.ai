# Arogyam: Route and Realtime Event Inventory

Date: 2026-04-11
Source: backend/app.py

## 1. HTTP Routes

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

## 2. SocketIO Events

| Event | Direction | Purpose |
|---|---|---|
| join_room | client -> server | Join doctor/patient signaling room |
| start_call | client -> server | Notify peer of incoming call |
| webrtc_offer | client -> server -> peer | Relay WebRTC offer SDP |
| webrtc_answer | client -> server -> peer | Relay WebRTC answer SDP |
| webrtc_ice_candidate | client -> server -> peer | Relay ICE candidates |
| connect | socket lifecycle | Log socket connection |
| disconnect | socket lifecycle | Log socket disconnection |

## 3. Logical Grouping

### 3.1 Authentication and portal routes
- /doctor, /patient, /pharmacist
- /submit, /pmain, /doctor_signup, /doctor_login, /pharmacist_login
- /logout

### 3.2 Consultation and messaging routes
- /chat/<doctor_id>/<patient_id>
- /chat_with_patient/<doctor_id>/<patient_id>
- /send_message
- /get_messages/<doctor_id>/<patient_id>
- /pay/<doctor_id>/<patient_id>

### 3.3 Prescription and pharmacy routes
- /give_prescription/<doctor_id>/<patient_id>
- /save_prescription
- /api/draft_prescription/<doctor_id>/<patient_id>
- /api/verify_prescription
- /get_prescriptions/<patient_id>
- /view_prescriptions/<doctor_id>/<patient_id>
- /api/get_pharmacists
- /api/create_order
- /api/update_order_status
- /patient_orders/<patient_id>

### 3.4 AI specialist routes
- /index
- /specialists
- /chat/<specialist_type>
- /api/chat
- /api/upload
- /api/clear-session
- /api/patient-info

### 3.5 Realtime signaling routes/events
- join_room
- start_call
- webrtc_offer
- webrtc_answer
- webrtc_ice_candidate

## 4. Important Note
There are two chat route patterns in the app:
- /chat/<int:doctor_id>/<int:patient_id> for human doctor consultation
- /chat/<specialist_type> for AI specialist consultation

Route declarations are both valid because Flask resolves the integer converter route only when path segments are integers, and the specialist route for text keys.
