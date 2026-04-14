import json
import os
import re
from typing import Dict, List, Optional, Tuple


try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None

try:
    import httpx
    import base64
    HAS_MISTRAL_API = True
except Exception:  # pragma: no cover
    HAS_MISTRAL_API = False

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


# ---------------------------------------------------------------------------
# Deep clinical-reasoning prompts per specialist.
# Each one tells the model HOW to think, not just keywords to mention.
# ---------------------------------------------------------------------------
SPECIALIST_PROMPTS = {
    "neurologist": (
        "You think like a board-certified neurologist.\n"
        "For EVERY presentation:\n"
        "1. LOCALIZE the lesion: cortical · subcortical · brainstem · spinal · peripheral nerve · neuromuscular junction · muscle.\n"
        "2. Determine PATHOPHYSIOLOGY: vascular · inflammatory · degenerative · neoplastic · traumatic · metabolic/toxic · infectious.\n"
        "3. Apply TEMPORAL PATTERN: hyperacute (seconds-minutes → stroke) · acute (hours-days → infection/trauma) · "
        "subacute (weeks → autoimmune/tumor) · chronic (months-years → degenerative).\n"
        "4. RED FLAGS you MUST screen: thunderclap headache, new focal deficit, seizure with fever, "
        "progressive ascending weakness (GBS), cauda equina signs (saddle anesthesia + bladder dysfunction), "
        "papilledema, altered consciousness.\n"
        "5. Key exam findings to ask about: cranial nerve function, motor strength & tone, sensory modalities, "
        "deep tendon reflexes, gait & coordination, mental status.\n"
        "6. Common differentials to consider by chief complaint:\n"
        "   - Headache → tension vs migraine vs cluster vs secondary (SAH, meningitis, mass)\n"
        "   - Dizziness → BPPV vs vestibular neuritis vs central (stroke, MS)\n"
        "   - Weakness → UMN vs LMN pattern, myopathy vs neuropathy\n"
        "   - Numbness → dermatomal vs stocking-glove vs hemisensory"
    ),
    "cardiologist": (
        "You think like a board-certified cardiologist.\n"
        "For EVERY presentation:\n"
        "1. RISK STRATIFY immediately: Use age, gender, HTN, DM, smoking, dyslipidemia, family history.\n"
        "2. Apply the CHEST PAIN ALGORITHM:\n"
        "   - Cardiac (pressure/squeezing, exertional, radiating to arm/jaw, associated with diaphoresis)\n"
        "   - Pleuritic (sharp, worse with breathing → PE, pericarditis, pneumonia)\n"
        "   - Musculoskeletal (reproducible with palpation)\n"
        "   - GI (burning, positional, related to meals)\n"
        "3. For palpitations: determine if regular vs irregular, sustained vs paroxysmal, associated hemodynamic symptoms.\n"
        "4. RED FLAGS you MUST screen: ongoing chest pain at rest, syncope with exertion, "
        "acute dyspnea with pleuritic pain (PE), new murmur with fever (endocarditis), "
        "severe tearing back pain (aortic dissection), bilateral leg edema with orthopnea (CHF).\n"
        "5. Key history to ask: exercise tolerance (NYHA class), orthopnea/PND, "
        "ankle swelling, prior ECG/echo/stress test results, medications (especially anticoagulants, antihypertensives).\n"
        "6. Common differentials by presentation:\n"
        "   - Chest pain → ACS vs GERD vs costochondritis vs PE vs aortic dissection\n"
        "   - Dyspnea → CHF vs asthma vs PE vs anemia vs anxiety\n"
        "   - Palpitations → SVT vs AF vs PVCs vs anxiety vs thyroid"
    ),
    "orthopedic": (
        "You think like a board-certified orthopedic surgeon.\n"
        "For EVERY presentation:\n"
        "1. ANATOMICAL LOCALIZATION: Which joint/bone/region? Periarticular vs articular vs bony.\n"
        "2. MECHANISM: Traumatic vs atraumatic vs overuse vs degenerative.\n"
        "3. Apply the PAIN PATTERN analysis:\n"
        "   - Mechanical pain (worse with activity, better with rest) → degenerative, mechanical\n"
        "   - Inflammatory pain (morning stiffness >30 min, worse at rest, improves with activity) → RA, SpA\n"
        "   - Night pain (constant, disturbs sleep) → infection, tumor, fracture\n"
        "4. RED FLAGS you MUST screen: inability to bear weight, visible deformity, "
        "neurovascular compromise (numbness/tingling distal to injury, loss of pulse), "
        "open fracture, compartment syndrome signs (pain out of proportion, pain with passive stretch), "
        "night pain + weight loss (malignancy), fever + joint swelling (septic joint).\n"
        "5. Key history: injury mechanism, weight-bearing status, swelling onset/timing, "
        "locking/catching/giving way, prior imaging, occupational/sports demands.\n"
        "6. Common differentials by region:\n"
        "   - Knee → ACL/meniscus tear vs OA vs patellofemoral syndrome vs bursitis\n"
        "   - Shoulder → rotator cuff vs frozen shoulder vs impingement vs instability\n"
        "   - Back → disc herniation vs spinal stenosis vs muscle strain vs fracture"
    ),
    "general_practitioner": (
        "You think like an experienced general practitioner/internist.\n"
        "For EVERY presentation:\n"
        "1. SYSTEMS REVIEW: Systematically screen major organ systems to identify which may be involved.\n"
        "2. Apply the TRIAGE approach:\n"
        "   - Is this EMERGENT (needs ER now)?\n"
        "   - Is this URGENT (needs evaluation within 24-48 hours)?\n"
        "   - Is this ROUTINE (can be managed with advice and follow-up)?\n"
        "3. Consider COMMON conditions first (Occam's razor), then serious conditions to rule out.\n"
        "4. RED FLAGS for immediate referral: chest pain, sudden severe headache, "
        "difficulty breathing, one-sided weakness, high fever with neck stiffness, "
        "uncontrolled bleeding, severe abdominal pain.\n"
        "5. Ask about: onset, duration, progression, aggravating/relieving factors, "
        "associated symptoms, past medical history, medications, allergies, family history, lifestyle.\n"
        "6. KEY PRINCIPLE: Don't anchor on the first diagnosis. Generate at least 3 differentials "
        "spanning different body systems when the presentation is ambiguous."
    ),
    "pulmonologist": (
        "You think like a board-certified pulmonologist.\n"
        "For EVERY presentation:\n"
        "1. CHARACTERIZE the respiratory symptom:\n"
        "   - Cough: productive vs dry, duration (acute <3w, subacute 3-8w, chronic >8w), timing, triggers\n"
        "   - Dyspnea: at rest vs exertional, acute vs chronic, orthopnea/PND present?\n"
        "   - Wheeze: inspiratory (upper airway) vs expiratory (lower airway)\n"
        "2. Apply the ACUTE vs CHRONIC framework:\n"
        "   - Acute cough → URI, pneumonia, PE, asthma exacerbation, foreign body\n"
        "   - Chronic cough → asthma, GERD, post-nasal drip, ACE inhibitor, COPD, TB, malignancy\n"
        "3. RED FLAGS you MUST screen: hemoptysis, sudden pleuritic chest pain with dyspnea (PE), "
        "stridor (upper airway emergency), oxygen saturation <92%, inability to speak in full sentences, "
        "fever with rigors and productive cough (pneumonia/abscess), weight loss + night sweats (TB/cancer).\n"
        "4. Key history: smoking pack-years, occupational exposures, asthma/allergy history, "
        "TB contact/travel, recent surgery/immobilization (VTE risk), medication history (ACE inhibitors).\n"
        "5. Common differentials:\n"
        "   - Acute dyspnea → asthma vs pneumonia vs PE vs pneumothorax vs CHF exacerbation\n"
        "   - Chronic cough → asthma vs GERD vs postnasal drip vs COPD vs TB"
    ),
    "dentist": (
        "You think like an experienced dentist/oral medicine specialist.\n"
        "For EVERY presentation:\n"
        "1. LOCALIZE the pain: specific tooth vs quadrant vs jaw vs referred pain.\n"
        "2. CHARACTERIZE:\n"
        "   - Sharp vs dull vs throbbing\n"
        "   - Spontaneous vs provoked (hot, cold, sweet, biting)\n"
        "   - Duration of pain after stimulus (seconds = reversible pulpitis, minutes = irreversible)\n"
        "3. Apply PULPAL DIAGNOSIS framework:\n"
        "   - Normal pulp → reversible pulpitis → irreversible pulpitis → necrosis → abscess\n"
        "4. RED FLAGS you MUST screen: facial swelling spreading to floor of mouth/neck (Ludwig's angina), "
        "difficulty breathing/swallowing from dental infection, trismus, fever with facial cellulitis, "
        "uncontrolled bleeding post-extraction, numbness of lip/chin (nerve involvement).\n"
        "5. Key history: dental hygiene habits, last dental visit, trauma history, "
        "recent dental work, sensitivity timeline, bleeding gums pattern.\n"
        "6. Common differentials:\n"
        "   - Tooth pain → caries vs crack vs periapical abscess vs periodontal abscess\n"
        "   - Gum issues → gingivitis vs periodontitis vs pericoronitis vs oral ulcers\n"
        "   - Jaw pain → TMJ dysfunction vs bruxism vs odontogenic vs referred cardiac pain"
    ),
    "dermatologist": (
        "You think like a board-certified dermatologist.\n"
        "For EVERY presentation:\n"
        "1. DESCRIBE the lesion using dermatological morphology:\n"
        "   - Primary: macule, patch, papule, plaque, nodule, vesicle, bulla, pustule, wheal\n"
        "   - Secondary: scale, crust, erosion, ulcer, atrophy, lichenification\n"
        "2. Apply the DISTRIBUTION PATTERN analysis:\n"
        "   - Localized vs generalized, symmetric vs asymmetric\n"
        "   - Sun-exposed vs covered areas, flexural vs extensor, dermatomal\n"
        "3. ABCDE rule for pigmented lesions: Asymmetry, Border irregularity, Color variation, "
        "Diameter >6mm, Evolution/change over time.\n"
        "4. RED FLAGS you MUST screen: rapidly expanding erythema with fever (necrotizing fasciitis/cellulitis), "
        "purpura that doesn't blanch (vasculitis/meningococcemia), widespread blistering with mucous membrane "
        "involvement (SJS/TEN), new mole with ABCDE features (melanoma), erythroderma (>90% body surface).\n"
        "5. Key history: duration, progression, itch vs pain, triggers (sun, food, contact, stress), "
        "new products/medications, atopic history, family history, prior treatments tried.\n"
        "6. Common differentials by pattern:\n"
        "   - Itchy rash → eczema vs contact dermatitis vs urticaria vs scabies vs fungal\n"
        "   - Scaling plaques → psoriasis vs tinea vs eczema vs pityriasis rosea\n"
        "   - Acne-like → acne vulgaris vs rosacea vs folliculitis vs perioral dermatitis"
    ),
    "gynecologist": (
        "You think like a board-certified gynecologist.\n"
        "For EVERY presentation:\n"
        "1. MENSTRUAL HISTORY is mandatory: LMP, cycle length, regularity, flow volume, "
        "intermenstrual bleeding, postmenopausal bleeding.\n"
        "2. REPRODUCTIVE STATUS assessment:\n"
        "   - Rule out pregnancy in reproductive-age women with relevant symptoms\n"
        "   - Determine menopausal status and HRT use\n"
        "3. Apply the PELVIC PAIN ALGORITHM:\n"
        "   - Acute → ectopic pregnancy, ovarian torsion, ruptured cyst, PID, appendicitis\n"
        "   - Chronic → endometriosis, adenomyosis, fibroids, chronic PID, adhesions\n"
        "   - Cyclic vs non-cyclic pattern\n"
        "4. RED FLAGS you MUST screen: positive pregnancy test + acute pelvic pain +/- vaginal bleeding "
        "(ectopic until proven otherwise), heavy vaginal bleeding with hemodynamic instability, "
        "postmenopausal bleeding (endometrial cancer risk), acute abdomen with ovarian mass (torsion), "
        "fever + purulent discharge + cervical motion tenderness (PID).\n"
        "5. Key history: obstetric history (G_P_), contraception, sexual history/STI risk, "
        "Pap smear history, prior gynecological surgeries, urinary/bowel symptoms.\n"
        "6. Common differentials:\n"
        "   - Abnormal bleeding → fibroids vs polyps vs hormonal vs malignancy\n"
        "   - Discharge → physiological vs candida vs BV vs trichomoniasis vs cervicitis\n"
        "   - Pelvic pain → endometriosis vs ovarian cyst vs PID vs fibroid"
    ),
}


# ---------------------------------------------------------------------------
# Richer, clinically-grounded follow-up questions per specialist.
# These serve as the FALLBACK question bank; the live model generates
# context-aware questions from the system prompt.
# ---------------------------------------------------------------------------
FOLLOW_UP_QUESTIONS = {
    "neurologist": [
        "When exactly did these symptoms start — was the onset sudden (seconds/minutes) or gradual (days/weeks)? This helps distinguish vascular from progressive causes.",
        "Are symptoms constant, or do they come and go? If episodic, how long does each episode last and how often do they occur?",
        "Do you have any associated symptoms: headache, vision changes, numbness/tingling, muscle weakness, difficulty speaking, balance problems, or changes in memory/thinking?",
        "Any recent head injury, fever, neck stiffness, seizures, or the 'worst headache of your life'? These are critical red flags.",
    ],
    "cardiologist": [
        "Describe your chest discomfort precisely — is it pressure/squeezing, sharp/stabbing, or burning? Does it radiate to your arm, jaw, neck, or back?",
        "Does the discomfort come on with physical exertion (walking, climbing stairs) and go away with rest? How far can you walk before symptoms start?",
        "Do you experience any of these: palpitations (heart racing/skipping), dizziness/lightheadedness, fainting spells, or waking up at night short of breath?",
        "What are your known risk factors: high blood pressure, diabetes, high cholesterol, smoking, family history of heart disease before age 55 (men) or 65 (women)?",
    ],
    "orthopedic": [
        "Which specific area is affected? Did this start after an injury (fall, twist, impact) or did it come on without a clear cause?",
        "Describe the pain: is it a sharp/stabbing pain, a dull ache, or a throbbing sensation? Rate it 0-10. Is it worse in the morning, at night, or with specific movements?",
        "Can you bear weight on it / use it normally? Is there visible swelling, bruising, deformity, or locking/catching/giving way?",
        "Have you had any prior injuries, surgeries, or imaging (X-ray, MRI) of this area? What treatments have you tried so far?",
    ],
    "general_practitioner": [
        "When did your symptoms begin, and have they been getting better, worse, or staying the same? Was the onset sudden or gradual?",
        "Do you have any of these general symptoms: fever, chills, fatigue, unintended weight change, night sweats, appetite changes, or sleep difficulties?",
        "Do you have any chronic medical conditions (diabetes, hypertension, thyroid, etc.)? Are you currently taking any medications, vitamins, or supplements?",
        "Any recent travel, sick contacts, new medications, major stress, or changes in your daily routine?",
    ],
    "pulmonologist": [
        "Describe your breathing difficulty: is it at rest or only with exertion? Can you lie flat without feeling short of breath? How many pillows do you sleep with?",
        "If you have a cough, is it dry or producing phlegm/sputum? What color is the sputum? Any blood in it? How long have you had the cough?",
        "Any wheezing, chest tightness, or noisy breathing? Are symptoms worse at night, early morning, or triggered by exercise, cold air, dust, or allergens?",
        "What is your smoking history (current/former/never, how many years, packs per day)? Any occupational exposures (dust, chemicals, asbestos)? History of asthma or allergies?",
    ],
    "dentist": [
        "Point to exactly where the pain is — is it a specific tooth, the gums around a tooth, or a broader area of the jaw? Does it radiate to the ear, temple, or eye?",
        "What triggers the pain: hot foods/drinks, cold, sweets, biting down, or does it come on spontaneously? After the trigger is removed, how long does the pain last?",
        "Is there any swelling (inside the mouth or on the face/cheek), gum bleeding, pus discharge, bad taste in your mouth, or loose teeth?",
        "When was your last dental checkup? Any recent dental procedures, trauma to the teeth, or history of grinding/clenching at night?",
    ],
    "dermatologist": [
        "Where exactly is the skin problem located? Has it stayed in one area or spread? If it spread, describe the pattern (outward from center, appearing in new random areas, etc.).",
        "Describe what you see: is it raised or flat, red or discolored, dry/scaly, blistered, or oozing? Is it itchy, painful, burning, or asymptomatic?",
        "How long has this been present? Has it changed in size, color, or shape? Does it come and go, or is it persistent? Any previous similar episodes?",
        "Any new products (soap, detergent, cosmetics, sunscreen), medications, foods, or exposures before this started? Do you have a personal or family history of eczema, asthma, or psoriasis?",
    ],
    "gynecologist": [
        "When was your last menstrual period? Are your periods regular (every 21-35 days)? How many days does your period last, and how heavy is the flow?",
        "Describe your main symptom in detail: if pain — where exactly, what kind of pain (cramping, sharp, dull), does it relate to your menstrual cycle? If discharge — what color, odor, consistency?",
        "Is there any possibility of pregnancy? What contraception do you use? Any history of sexually transmitted infections?",
        "Any prior gynecological conditions (fibroids, cysts, endometriosis, PCOS), surgeries, or abnormal Pap smears? How many pregnancies and deliveries have you had?",
    ],
}


SECTION_ORDER = [
    ("symptoms_summary", "1. 🧾 Symptoms Summary"),
    ("additional_questions", "2. ❓ Additional Questions (if needed)"),
    ("possible_conditions", "3. 🧠 Possible Conditions"),
    ("recommended_tests", "4. 🧪 Recommended Tests"),
    ("general_suggestions", "5. 💊 General Suggestions"),
    ("disclaimer", "6. ⚠️ Disclaimer"),
]


class GroqChatClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.client = None
        if Groq and api_key:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.client = None

    # ------------------------------------------------------------------
    # System prompt — compact, focused, with a concrete example
    # ------------------------------------------------------------------
    def _build_system_prompt(self, specialist_type: str) -> str:
        specialist_rules = SPECIALIST_PROMPTS.get(
            specialist_type,
            SPECIALIST_PROMPTS["general_practitioner"],
        )
        specialist_name = specialist_type.replace("_", " ").title()

        return f"""You are an expert {specialist_name} AI medical consultant. You provide thoughtful, evidence-based medical guidance while maintaining clinical caution.

=== YOUR CLINICAL THINKING PROCESS ===

{specialist_rules}

=== HOW TO RESPOND ===

ALWAYS use this exact structure. Every section must contain substantive clinical content, not placeholder text.

1. 🧾 Symptoms Summary
   Concisely restate what the patient described. Include relevant positives AND negatives.

2. ❓ Additional Questions (if needed)
   Ask 2-4 TARGETED questions based on what the patient actually said. Each question should help you narrow the differential. Explain briefly WHY you're asking.

3. 🧠 Possible Conditions
   List 3-5 conditions from most to least likely. For EACH:
   - Name the condition clearly
   - [HIGH/MODERATE/LOW confidence]
   - Explain in 2-3 sentences WHY this fits or doesn't fully fit the presentation
   - Mention key distinguishing features

4. 🧪 Recommended Tests
   Suggest specific, relevant investigations. For each test, briefly state what it would confirm or rule out.

5. 💊 General Suggestions
   - Immediate self-care advice if appropriate
   - When to seek urgent medical attention (specific symptoms to watch for)
   - Lifestyle modifications relevant to the presentation
   - Whether specialist referral is recommended and why

6. ⚠️ Disclaimer
   Brief standard disclaimer (1-2 lines max). Do not repeat it multiple times.

=== RESPONSE FORMAT GUIDE ===

When a patient describes symptoms, your response MUST follow this exact structure:

1. 🧾 Symptoms Summary
   → Summarize ONLY what the patient actually told you. Do NOT invent or assume symptoms.

2. ❓ Additional Questions (if needed)
   → Ask 2-4 targeted questions that are directly relevant to what the patient said.
   → Briefly explain WHY each question matters for narrowing the diagnosis.

3. 🧠 Possible Conditions
   → List 3-5 conditions, most likely first.
   → For each: name, [HIGH/MODERATE/LOW confidence], 2-3 sentences of clinical reasoning.

4. 🧪 Recommended Tests
   → List specific, relevant tests and what each one would confirm or rule out.

5. 💊 General Suggestions
   → Self-care, red flags, lifestyle advice, referral recommendation.

6. ⚠️ Disclaimer
   → 1-2 lines only. Do not repeat.

=== RULES ===

- Think step-by-step through your differential BEFORE writing
- Use "suggestive of," "consistent with," "consider" — never give definitive diagnoses
- When you're uncertain, say so honestly and recommend professional evaluation
- Tailor questions and differentials to WHAT THE PATIENT ACTUALLY SAID — do not ask generic questions that ignore their input
- If the patient provides follow-up information, REFINE your differential — don't just repeat the previous response
- For follow-up turns: acknowledge new information, explain how it changes your assessment, update differentials
- Be empathetic but clinically precise
- CRITICAL: NEVER invent or assume patient demographics (age, gender, occupation), symptoms, or history that the patient did NOT explicitly state. Base your entire response ONLY on what the patient actually wrote. If they only said "hello", ask them to describe their symptoms — do not fabricate a patient case.""".strip()


    # ------------------------------------------------------------------
    # Structured fallback: used only when the AI model is unavailable.
    # Provides genuinely useful guidance, not placeholder text.
    # ------------------------------------------------------------------
    def _build_structured_fallback(
        self,
        specialist_type: str,
        patient_data: Dict,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        image_context: Optional[str] = None,
    ) -> str:
        conversation_history = conversation_history or []
        user_turns = len([item for item in conversation_history if item.get("user")]) + 1

        symptoms = (user_message or patient_data.get("symptoms") or "No symptom details provided.").strip()
        specialist_name = specialist_type.replace("_", " ").title()
        followups = FOLLOW_UP_QUESTIONS.get(
            specialist_type,
            FOLLOW_UP_QUESTIONS["general_practitioner"],
        )

        summary_line = f"You reported: {symptoms}"
        if image_context:
            summary_line += "\n- Image findings: " + image_context[:300] + ("..." if len(image_context) > 300 else "")

        response_lines = [
            "1. 🧾 Symptoms Summary",
            f"- {summary_line}",
            "",
        ]

        # Additional questions — only on early turns
        response_lines.append("2. ❓ Additional Questions (if needed)")
        if user_turns <= 2:
            for q in followups[:3]:
                response_lines.append(f"- {q}")
        else:
            response_lines.append("- Based on the information you've provided, I have a reasonable picture. Please share any additional details you think are relevant.")
        response_lines.append("")

        # Possible conditions — honest about limitations
        response_lines.append("3. 🧠 Possible Conditions")
        response_lines.append(
            f"- Based on your description, a {specialist_name} would consider several conditions. "
            "However, I need to provide this assessment through our AI model which is temporarily processing your request. "
            "The conditions to consider depend on the specific combination of your symptoms, their duration, and your medical history."
        )
        response_lines.append(
            "- To give you accurate possible diagnoses, please ensure you've described: "
            "(a) exactly what you feel, (b) when it started, (c) what makes it better or worse, "
            "and (d) any other symptoms you've noticed."
        )
        response_lines.append("")

        # Recommended tests
        response_lines.append("4. 🧪 Recommended Tests")
        response_lines.append(
            f"- A {specialist_name} consultation (in-person) would include a targeted physical examination "
            "and may recommend specific diagnostic tests based on examination findings."
        )
        response_lines.append(
            "- General baseline tests that may be relevant: complete blood count (CBC), basic metabolic panel, "
            "and specialty-specific investigations as determined by your doctor."
        )
        response_lines.append("")

        # General suggestions
        response_lines.append("5. 💊 General Suggestions")
        response_lines.append("- Please provide more details about your symptoms so I can give you more specific guidance.")
        response_lines.append(
            "- **Seek immediate medical attention if you experience**: "
            "severe pain, difficulty breathing, chest pain, sudden weakness or numbness, "
            "high fever (>102°F/39°C), uncontrolled bleeding, or any rapidly worsening symptoms."
        )
        response_lines.append(f"- Consider scheduling a visit with a {specialist_name} for a proper clinical evaluation.")
        response_lines.append("")

        # Disclaimer — short, not repetitive
        response_lines.extend([
            "6. ⚠️ Disclaimer",
            "- This is educational guidance, not a medical diagnosis. Please consult a qualified healthcare professional for proper evaluation and treatment.",
        ])

        return "\n".join(response_lines)

    def _normalize_for_match(self, text: str) -> str:
        lowered = text.lower()
        chars = []
        for ch in lowered:
            if ch.isalnum() or ch.isspace():
                chars.append(ch)
            else:
                chars.append(" ")
        return " ".join("".join(chars).split())

    def _match_section_key(self, line: str) -> Optional[str]:
        normalized = self._normalize_for_match(line)

        if "symptom" in normalized and "summary" in normalized:
            return "symptoms_summary"
        if "additional" in normalized and "question" in normalized:
            return "additional_questions"
        if "possible" in normalized and "condition" in normalized:
            return "possible_conditions"
        if "recommended" in normalized and "test" in normalized:
            return "recommended_tests"
        if "general" in normalized and "suggestion" in normalized:
            return "general_suggestions"
        if "disclaimer" in normalized or "discl" in normalized:
            return "disclaimer"
        return None

    def _extract_sections(self, text: str) -> Dict[str, List[str]]:
        sections = {key: [] for key, _ in SECTION_ORDER}
        current_key = None

        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue

            section_key = self._match_section_key(line)
            if section_key:
                current_key = section_key
                continue

            if current_key:
                if line.startswith(("-", "*")):
                    bullet_line = line
                else:
                    bullet_line = f"- {line}"
                sections[current_key].append(bullet_line)

        return sections

    # ------------------------------------------------------------------
    # Structured output enforcer — gentler, doesn't destroy good content
    # ------------------------------------------------------------------
    def _enforce_structured_output(
        self,
        content: str,
        specialist_type: str,
        patient_data: Dict,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        image_context: Optional[str] = None,
    ) -> str:
        generated_sections = self._extract_sections(content)

        # Count how many sections actually have content
        filled_sections = sum(1 for k in generated_sections if generated_sections[k])

        # If the model produced a good response with most sections, use it as-is
        # Only fill in truly empty critical sections
        if filled_sections >= 4:
            # Good response — just ensure disclaimer exists
            if not generated_sections.get("disclaimer"):
                generated_sections["disclaimer"] = [
                    "- This is educational guidance, not a medical diagnosis. Please consult a qualified healthcare professional for proper evaluation and treatment."
                ]
        else:
            # Sparse response — fill empty sections with minimal helpful defaults
            fallback = self._build_structured_fallback(
                specialist_type=specialist_type,
                patient_data=patient_data,
                user_message=user_message,
                conversation_history=conversation_history,
                image_context=image_context,
            )
            fallback_sections = self._extract_sections(fallback)

            for section_key, _ in SECTION_ORDER:
                if not generated_sections.get(section_key):
                    generated_sections[section_key] = fallback_sections.get(section_key, [])

        # Ensure disclaimer always has the core statement
        disclaimer_lines = generated_sections.get("disclaimer", [])
        disclaimer_joined = " ".join(line.lower() for line in disclaimer_lines)
        if "not a medical diagnosis" not in disclaimer_joined and "not a diagnosis" not in disclaimer_joined:
            disclaimer_lines.insert(0, "- This is educational guidance, not a medical diagnosis. Please consult a qualified healthcare professional for proper evaluation and treatment.")
        generated_sections["disclaimer"] = disclaimer_lines

        # Build final output
        lines = []
        for section_key, heading in SECTION_ORDER:
            lines.append(heading)
            section_lines = generated_sections.get(section_key, [])
            if section_lines:
                lines.extend(section_lines)
            lines.append("")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Build a brief summary of earlier conversation for context
    # ------------------------------------------------------------------
    def _summarize_history(self, conversation_history: List[Dict]) -> str:
        if not conversation_history:
            return ""

        summary_parts = []
        for i, turn in enumerate(conversation_history):
            user_text = turn.get("user", "")
            assistant_text = turn.get("assistant", "")

            # Extract key symptoms mentioned by user (first 150 chars)
            if user_text:
                summary_parts.append(f"Patient (turn {i+1}): {user_text[:150]}{'...' if len(user_text) > 150 else ''}")

            # Extract key findings from assistant (look for conditions section)
            if assistant_text and "Possible Conditions" in assistant_text:
                # Get just the conditions mentioned
                conditions_start = assistant_text.find("Possible Conditions")
                conditions_end = assistant_text.find("Recommended Tests", conditions_start)
                if conditions_end == -1:
                    conditions_end = conditions_start + 500
                conditions_snippet = assistant_text[conditions_start:conditions_end].strip()[:200]
                summary_parts.append(f"Assessment (turn {i+1}): {conditions_snippet}...")

        return "\n".join(summary_parts) if summary_parts else ""

    # ------------------------------------------------------------------
    # Main chat method
    # ------------------------------------------------------------------
    # Words that indicate the user is just greeting, not describing symptoms
    _GREETING_PATTERNS = {
        "hello", "hi", "hey", "helo", "hii", "good morning", "good afternoon",
        "good evening", "good night", "greetings", "howdy", "hello doctor",
        "hi doctor", "hey doctor", "hello doc", "hi doc", "namaste", "vanakkam",
        "namaskar", "hola", "bonjour", "how are you", "how r u",
    }

    def _is_greeting_only(self, message: str) -> bool:
        """Returns True if the message is ONLY a greeting with no symptom information."""
        cleaned = message.strip().lower().rstrip("!.,?")
        return cleaned in self._GREETING_PATTERNS

    def _greeting_response(self, specialist_type: str) -> str:
        """Return a proper welcome message that asks the patient to describe their symptoms."""
        specialist_name = specialist_type.replace("_", " ").title()
        return (
            f"1. 🧾 Symptoms Summary\n"
            f"- No symptoms described yet.\n\n"
            f"2. ❓ Additional Questions (if needed)\n"
            f"- Hello! I'm your AI {specialist_name}. To help you properly, please describe your symptoms.\n"
            f"- What are you experiencing? Please include: what the problem is, how long it has been going on, "
            f"where it is located (if relevant), and anything that makes it better or worse.\n\n"
            f"3. 🧠 Possible Conditions\n"
            f"- I need more information about your symptoms before I can suggest possible conditions. "
            f"Please describe what you are experiencing.\n\n"
            f"4. 🧪 Recommended Tests\n"
            f"- Tests will be suggested after you describe your symptoms.\n\n"
            f"5. 💊 General Suggestions\n"
            f"- Please share your symptoms so I can provide personalized guidance.\n\n"
            f"6. ⚠️ Disclaimer\n"
            f"- This is educational guidance, not a medical diagnosis. Please consult a qualified healthcare professional for proper evaluation and treatment."
        )

    def chat(
        self,
        specialist_type: str,
        patient_data: Dict,
        user_message: str = "",
        conversation_history: Optional[List[Dict]] = None,
        image_context: Optional[str] = None,
    ) -> str:
        conversation_history = conversation_history or []

        if not user_message:
            user_message = patient_data.get("symptoms", "")

        # Guard: if the user only sent a greeting with no symptoms, return a
        # friendly welcome message instead of letting the model hallucinate
        if self._is_greeting_only(user_message):
            return self._greeting_response(specialist_type)

        if self.client:
            try:
                messages = [{"role": "system", "content": self._build_system_prompt(specialist_type)}]

                # Build conversation context from recent history
                recent_history = conversation_history[-6:]

                # If there's older history, add a summary
                if len(conversation_history) > 6:
                    older_history = conversation_history[:-6]
                    summary = self._summarize_history(older_history)
                    if summary:
                        messages.append({
                            "role": "user",
                            "content": f"[Previous conversation summary for context]\n{summary}"
                        })
                        messages.append({
                            "role": "assistant",
                            "content": "Understood. I have the previous context. Please continue with your current question."
                        })

                # Add recent conversation turns
                for turn in recent_history:
                    user_text = turn.get("user")
                    assistant_text = turn.get("assistant")
                    if user_text:
                        messages.append({"role": "user", "content": user_text})
                    if assistant_text:
                        messages.append({"role": "assistant", "content": assistant_text})

                # Build the current user message in natural language
                turn_number = len([item for item in conversation_history if item.get("user")]) + 1

                # Filter patient_data to only include actually-known information
                known_patient_info = []
                age = patient_data.get("age")
                gender = patient_data.get("gender")
                if age and age not in ("Not specified", "Unknown", ""):
                    known_patient_info.append(f"Age: {age}")
                if gender and gender not in ("Not specified", "Unknown", ""):
                    known_patient_info.append(f"Gender: {gender}")

                # Add any specialist-specific fields that have real values
                skip_fields = {"name", "age", "gender", "symptoms"}
                noise_values = {"Not specified", "Not measured", "Not available", "None reported",
                                "Not specified ", "Unknown", "See description", "Recent", "Normal", ""}
                for key, value in patient_data.items():
                    if key in skip_fields:
                        continue
                    if isinstance(value, str) and value.strip() in noise_values:
                        continue
                    if value:
                        known_patient_info.append(f"{key.replace('_', ' ').title()}: {value}")

                # Construct the user message naturally
                user_prompt_parts = [user_message]

                if known_patient_info:
                    patient_context = " | ".join(known_patient_info)
                    user_prompt_parts.append(f"\n[Patient context: {patient_context}]")

                if turn_number > 1:
                    user_prompt_parts.append(f"\n[This is follow-up turn {turn_number}. Refine your assessment based on this new information.]")

                if image_context:
                    # Integrate image findings naturally
                    user_prompt_parts.append(
                        f"\n[Medical image analysis is available. Integrate these findings into your clinical assessment:\n"
                        f"{image_context[:800]}]"
                    )

                current_message = "\n".join(user_prompt_parts)
                messages.append({"role": "user", "content": current_message})

                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2048,
                )
                content = completion.choices[0].message.content
                if content and content.strip():
                    return self._enforce_structured_output(
                        content=content.strip(),
                        specialist_type=specialist_type,
                        patient_data=patient_data,
                        user_message=user_message,
                        conversation_history=conversation_history,
                        image_context=image_context,
                    )
            except Exception:
                pass

        return self._build_structured_fallback(
            specialist_type=specialist_type,
            patient_data=patient_data,
            user_message=user_message,
            conversation_history=conversation_history,
            image_context=image_context,
        )

    def draft_prescription(self, chat_history: List[Dict]) -> str:
        """
        Reads a patient-doctor chat history and automatically drafts a clinical
        prescription using the Groq AI model. Returns a structured JSON string.
        """
        if not self.client or not chat_history:
            return '{"diagnosis": "", "medicines": [], "notes": "AI Scribe unavailable or no chat history."}'

        history_text = "\n".join([f"{msg.get('sender', 'Unknown').title()}: {msg.get('message', '')}" for msg in chat_history[-15:]])

        prompt = f"""You are an AI Medical Scribe. Read the following patient-doctor chat history and draft a prescription.
Return ONLY valid JSON with this exact structure (no markdown blocks, no intro text):
{{
    "diagnosis": "Main suspected condition or diagnosis",
    "medicines": [
        {{"name": "Drug Name", "dosage": "e.g., 500mg", "duration": "e.g., 5 days", "instructions": "e.g., after meals"}}
    ],
    "notes": "Any clinical notes or lifestyle advice discussed"
}}

CHAT HISTORY:
{history_text}
"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
            )
            # Find JSON block if the model wraps it
            response_text = completion.choices[0].message.content.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            return response_text
        except Exception as e:
            return f'{{"diagnosis": "", "medicines": [], "notes": "Error drafting: {str(e)}"}}'

    def verify_prescription_safety(self, diagnosis: str, age: str, medicines: list) -> str:
        """
        Uses an LLM to evaluate contraindications, age appropriateness, and multi-drug interactions 
        for a prescribed list of medicines. Returns structured JSON containing safety flags.
        """
        if not self.client or not medicines:
            return '{"safe": true, "warnings": [], "critical_alerts": []}'

        meds_text = ", ".join([f"{m.get('name')} ({m.get('dosage')})" for m in medicines])

        prompt = f"""You are an expert Clinical Pharmacologist AI.
Evaluate the following prescription for potential drug-drug interactions, contraindications based on diagnosis, and age-appropriateness.
Patient Age: {age}
Diagnosis: {diagnosis}
Prescribed Medicines: {meds_text}

Return ONLY valid JSON with this exact structure (no markdown blocks, no intro text):
{{
    "safe": false, // Set to true ONLY if absolutely zero interactions/contraindications are found.
    "warnings": ["List of minor side-effects or monitoring required"],
    "critical_alerts": ["List of FATAL or SEVERE contraindications/interactions, if any"]
}}
"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600,
            )
            response_text = completion.choices[0].message.content.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            return response_text
        except Exception as e:
            return f'{{"safe": false, "warnings": ["Error verifying safety: {str(e)}"], "critical_alerts": []}}'

    def _extract_json_object(self, text: str) -> Optional[Dict]:
        if not text:
            return None

        raw = text.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1 or last == -1 or last <= first:
            return None

        candidate = raw[first:last + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _conversation_to_pairs(self, conversation_history: List[Dict]) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []
        pending_user = ""

        for turn in conversation_history or []:
            if not isinstance(turn, dict):
                continue

            if "user" in turn or "assistant" in turn:
                user_text = str(turn.get("user", "")).strip()
                assistant_text = str(turn.get("assistant", "")).strip()
                if user_text:
                    pending_user = user_text
                if assistant_text:
                    if "how can i assist you today" in assistant_text.lower() and not pending_user:
                        continue
                    pairs.append((pending_user or "Patient follow-up", assistant_text))
                    pending_user = ""
                continue

            role = str(turn.get("type", "")).strip().lower()
            text = str(turn.get("text", "")).strip()
            if not text:
                continue

            if role == "user":
                pending_user = text
            elif role in {"bot", "assistant"}:
                if "how can i assist you today" in text.lower() and not pending_user:
                    continue
                pairs.append((pending_user or "Patient follow-up", text))
                pending_user = ""

        return pairs

    def _normalize_report_language(self, report_language: Optional[str]) -> str:
        normalized = str(report_language or "english").strip().lower()
        if normalized in {"ta", "tam", "tamil", "தமிழ்"}:
            return "tamil"
        return "english"

    def _normalize_report_mode(self, report_mode: Optional[str]) -> str:
        normalized = str(report_mode or "patient_simple").strip().lower().replace("-", "_")
        if normalized in {"doctor", "doctor_mode", "doctor_detailed", "clinical"}:
            return "doctor_detailed"
        if normalized in {"patient", "patient_standard", "standard"}:
            return "patient_standard"
        return "patient_simple"

    def _normalize_clarity_level(self, clarity_level: Optional[str], report_mode: str) -> str:
        normalized = str(clarity_level or "").strip().lower()
        if normalized in {"simple", "easy", "basic"}:
            return "simple"
        if normalized in {"detailed", "detail", "deep"}:
            return "detailed"
        if normalized in {"standard", "normal", "medium"}:
            return "standard"

        if report_mode == "doctor_detailed":
            return "detailed"
        if report_mode == "patient_standard":
            return "standard"
        return "simple"

    def _clean_report_point(self, point: str) -> str:
        text = str(point or "").replace("\r", " ").strip()
        if not text:
            return ""

        text = re.sub(r"^\s*[-*•]+\s*", "", text)
        text = re.sub(r"^\s*#{1,6}\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip(" :-")

        if not text:
            return ""
        if re.fullmatch(r"[\W_]+", text):
            return ""

        return text

    def _normalize_report_sections(self, raw_sections) -> List[Dict[str, List[str]]]:
        normalized_sections: List[Dict[str, List[str]]] = []
        if not isinstance(raw_sections, list):
            return normalized_sections

        for section in raw_sections:
            if not isinstance(section, dict):
                continue

            heading = str(section.get("heading", "")).strip()
            heading = re.sub(r"^\s*#{1,6}\s*", "", heading).strip(" :-")
            if not heading:
                continue

            points: List[str] = []
            points_raw = section.get("points", [])
            if isinstance(points_raw, list):
                for point in points_raw:
                    point_text = self._clean_report_point(point)
                    if point_text:
                        points.append(point_text)
            elif isinstance(points_raw, str):
                for line in points_raw.splitlines():
                    point_text = self._clean_report_point(line)
                    if point_text:
                        points.append(point_text)

            if points:
                normalized_sections.append({
                    "heading": heading[:90],
                    "points": points[:8],
                })

        return normalized_sections[:8]

    def _build_report_fallback(
        self,
        specialist_type: str,
        conversation_history: List[Dict],
        patient_data: Optional[Dict],
        report_language: str = "english",
        report_mode: str = "patient_simple",
        clarity_level: str = "simple",
    ) -> Dict:
        specialist_name = specialist_type.replace("_", " ").title()
        report_language = self._normalize_report_language(report_language)
        report_mode = self._normalize_report_mode(report_mode)
        clarity_level = self._normalize_clarity_level(clarity_level, report_mode)
        is_tamil = report_language == "tamil"
        pairs = self._conversation_to_pairs(conversation_history)

        if patient_data is None:
            patient_data = {}

        demographics = []
        age = str(patient_data.get("age", "")).strip()
        gender = str(patient_data.get("gender", "")).strip()
        if age and age.lower() not in {"not specified", "unknown"}:
            demographics.append(f"வயது: {age}" if is_tamil else f"Age: {age}")
        if gender and gender.lower() not in {"not specified", "unknown"}:
            demographics.append(f"பாலினம்: {gender}" if is_tamil else f"Gender: {gender}")

        if is_tamil:
            overview = "இந்த அறிக்கை உங்கள் AI மருத்துவ உரையாடலின் முக்கிய அம்சங்களை எளிய முறையில் விளக்குகிறது."
        else:
            overview = "This report summarizes your AI consultation in simplified language to help you understand the key points."

        if demographics:
            overview += " " + " | ".join(demographics)

        sections: List[Dict[str, List[str]]] = []
        for idx, (question, response) in enumerate(pairs[-6:], start=1):
            cleaned_response_lines = [
                self._clean_report_point(line)
                for line in str(response).splitlines()
                if line.strip()
            ]
            cleaned_response_lines = [line for line in cleaned_response_lines if line]

            if not cleaned_response_lines:
                fallback_point = self._clean_report_point(str(response).strip()[:320])
                if fallback_point:
                    cleaned_response_lines = [fallback_point]
                else:
                    cleaned_response_lines = [
                        "Model response could not be normalized cleanly."
                        if not is_tamil
                        else "மாதிரி பதிலை தெளிவாக சீரமைக்க முடியவில்லை."
                    ]

            question_prefix = "கேள்வி" if is_tamil else "Question"
            heading_prefix = "ஆலோசனை கட்டம்" if is_tamil else "Consultation Step"
            points = [f"{question_prefix}: {question.strip()[:220]}"] + cleaned_response_lines[:6]
            sections.append({
                "heading": f"{heading_prefix} {idx}",
                "points": points,
            })

        if not sections:
            empty_heading = "Current Status"
            empty_line_one = f"No complete consultation responses were found for {specialist_name}."
            empty_line_two = "Please ask at least one detailed symptom question to generate a full report."
            if is_tamil:
                empty_heading = "தற்போதைய நிலை"
                empty_line_one = f"{specialist_name} நிபுணருக்கான முழுமையான ஆலோசனை பதில்கள் இன்னும் இல்லை."
                empty_line_two = "முழு அறிக்கை உருவாக குறைந்தது ஒரு விரிவான அறிகுறி கேள்வியை கேளுங்கள்."

            sections = [
                {
                    "heading": empty_heading,
                    "points": [
                        empty_line_one,
                        empty_line_two,
                    ],
                }
            ]

        fallback_title = f"{specialist_name} Consultation Report"
        fallback_safety = "This summary is for understanding only and is not a final diagnosis. Please consult a licensed doctor for treatment decisions."
        if is_tamil:
            fallback_title = f"{specialist_name} ஆலோசனை அறிக்கை"
            fallback_safety = "இந்த சுருக்கம் புரிதலுக்காக மட்டுமே. இறுதி மருத்துவ தீர்மானங்களுக்கு தகுதியான மருத்துவரை அணுகவும்."

        return {
            "title": fallback_title,
            "overview": overview,
            "sections": sections,
            "safety_note": fallback_safety,
            "report_preferences": {
                "language": report_language,
                "mode": report_mode,
                "clarity": clarity_level,
            },
        }

    def generate_structured_report(
        self,
        specialist_type: str,
        conversation_history: List[Dict],
        patient_data: Optional[Dict] = None,
        report_language: str = "english",
        report_mode: str = "patient_simple",
        clarity_level: str = "simple",
    ) -> Dict:
        report_language = self._normalize_report_language(report_language)
        report_mode = self._normalize_report_mode(report_mode)
        clarity_level = self._normalize_clarity_level(clarity_level, report_mode)
        specialist_name = specialist_type.replace("_", " ").title()
        pairs = self._conversation_to_pairs(conversation_history)

        if not pairs:
            return self._build_report_fallback(
                specialist_type,
                conversation_history,
                patient_data,
                report_language,
                report_mode,
                clarity_level,
            )

        if not self.client:
            return self._build_report_fallback(
                specialist_type,
                conversation_history,
                patient_data,
                report_language,
                report_mode,
                clarity_level,
            )

        if patient_data is None:
            patient_data = {}

        patient_context_lines = []
        for key in ("name", "age", "gender"):
            value = str(patient_data.get(key, "")).strip()
            if value and value.lower() not in {"not specified", "unknown", "patient"}:
                patient_context_lines.append(f"{key.title()}: {value}")
        patient_context = " | ".join(patient_context_lines) if patient_context_lines else "Not provided"

        transcript_lines: List[str] = []
        for i, (question, answer) in enumerate(pairs[-10:], start=1):
            transcript_lines.append(f"User {i}: {question[:700]}")
            transcript_lines.append(f"Assistant {i}: {answer[:1400]}")
        transcript = "\n".join(transcript_lines)

        language_instruction = "Write all patient-facing values in English."
        heading_1 = "Symptoms Summary"
        heading_2 = "Possible Causes to Discuss"
        heading_3 = "Recommended Next Steps"
        heading_4 = "When to Seek Urgent Care"

        audience_instruction = "Audience: patient. Keep language simple and practical."
        if report_mode == "patient_standard":
            audience_instruction = "Audience: patient. Use clear but moderately detailed language."
        elif report_mode == "doctor_detailed":
            audience_instruction = "Audience: doctor/clinical reviewer. Include concise clinical reasoning and differentials."

        clarity_instruction = "Use very short and easy bullet points."
        if clarity_level == "standard":
            clarity_instruction = "Use balanced sentence length and moderate detail."
        elif clarity_level == "detailed":
            clarity_instruction = "Use detailed but organized bullet points with rationale."

        if report_language == "tamil":
            language_instruction = (
                "Write all patient-facing values in Tamil (தமிழ்). "
                "Use natural and simple spoken Tamil with short bullet points."
            )
            heading_1 = "அறிகுறிகள் சுருக்கம்"
            heading_2 = "பேச வேண்டிய சாத்திய காரணங்கள்"
            heading_3 = "அடுத்த பரிந்துரைக்கப்பட்ட படிகள்"
            heading_4 = "அவசர சிகிச்சை தேவைப்படும் அறிகுறிகள்"

        prompt = f"""Create a patient-friendly structured medical report from this conversation.

Specialist: {specialist_name}
Patient Context: {patient_context}
Output Language: {report_language}
Report Mode: {report_mode}
Clarity Level: {clarity_level}

Conversation Transcript:
{transcript}

Rules:
1. Use clear, simple language for patients.
2. Keep all points concise and easy to understand.
3. Do not add diagnoses that are not supported by the conversation.
4. If uncertain, explicitly mention uncertainty.
5. Include practical next steps and warning signs.
6. Do not use markdown, only JSON.
7. {language_instruction}
8. {audience_instruction}
9. {clarity_instruction}

Return ONLY valid JSON in this exact schema:
{{
  "title": "string",
  "overview": "2-4 lines summary in simple language",
  "sections": [
        {{"heading": "{heading_1}", "points": ["point", "point"]}},
        {{"heading": "{heading_2}", "points": ["point", "point"]}},
        {{"heading": "{heading_3}", "points": ["point", "point"]}},
        {{"heading": "{heading_4}", "points": ["point", "point"]}}
  ],
  "safety_note": "one short cautionary sentence"
}}"""

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a clinical communication expert. Convert medical chat into clear patient-friendly structured reports. Return JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1400,
            )
            content = completion.choices[0].message.content.strip()
            parsed = self._extract_json_object(content)
            if not parsed:
                return self._build_report_fallback(
                    specialist_type,
                    conversation_history,
                    patient_data,
                    report_language,
                    report_mode,
                    clarity_level,
                )

            title = str(parsed.get("title", "")).strip() or f"{specialist_name} Consultation Report"
            overview = str(parsed.get("overview", "")).strip()
            sections = self._normalize_report_sections(parsed.get("sections", []))
            safety_note = str(parsed.get("safety_note", "")).strip()

            if not overview or not sections:
                return self._build_report_fallback(
                    specialist_type,
                    conversation_history,
                    patient_data,
                    report_language,
                    report_mode,
                    clarity_level,
                )

            if not safety_note:
                if report_language == "tamil":
                    safety_note = "இந்த சுருக்கம் புரிதலுக்காக மட்டுமே; நேரடி மருத்துவ மதிப்பீட்டை மாற்றாது."
                else:
                    safety_note = "This summary is for understanding only and does not replace in-person medical evaluation."

            return {
                "title": title,
                "overview": overview,
                "sections": sections,
                "safety_note": safety_note,
                "report_preferences": {
                    "language": report_language,
                    "mode": report_mode,
                    "clarity": clarity_level,
                },
            }
        except Exception:
            return self._build_report_fallback(
                specialist_type,
                conversation_history,
                patient_data,
                report_language,
                report_mode,
                clarity_level,
            )


class VisionModelClient:
    def __init__(self, mistral_api_key=None):
        self.mistral_api_key = mistral_api_key
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "pixtral-12b-2409"

    def _detect_imaging_modality(self, filepath, filename, patient_info=None):
        """Detect imaging modality from filename, extension, and context."""
        filename_lower = filename.lower()

        modality_keywords = {
            'ct': ['ct', 'computed tomography', 'cat scan'],
            'mri': ['mri', 'magnetic resonance'],
            'xray': ['xray', 'x-ray', 'radiograph', 'chest', 'skeletal'],
            'ultrasound': ['ultrasound', 'us', 'sonography', 'echo'],
            'mammography': ['mammo', 'mammography'],
            'skin': ['derma', 'skin', 'lesion', 'rash', 'mole'],
            'endoscopy': ['endo', 'scope', 'gastro'],
            'pathology': ['pathology', 'histology', 'microscopy'],
        }

        for modality, keywords in modality_keywords.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return modality

        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.dcm', '.dicom']:
            return 'medical_imaging'

        return 'medical_imaging'

    def _encode_image_to_base64(self, filepath):
        """Convert image file to base64 for API transmission."""
        try:
            with open(filepath, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception:
            return None

    def _get_image_media_type(self, filepath):
        """Determine media type based on file extension."""
        ext = os.path.splitext(filepath)[1].lower()
        media_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.dcm': 'application/dicom',
            '.dicom': 'application/dicom'
        }
        return media_types.get(ext, 'image/jpeg')

    def _build_specialist_context(self, specialist_type):
        """Build specialist-specific context for prompts."""
        specialist_contexts = {
            'dermatologist': {
                'focus': 'dermatological conditions, skin pathology, and cutaneous findings',
                'key_areas': ['color', 'texture', 'morphology', 'borders', 'distribution', 'associated features'],
                'urgency_indicators': ['signs of skin cancer', 'severe inflammation', 'signs of infection'],
            },
            'cardiologist': {
                'focus': 'cardiac and cardiovascular imaging findings',
                'key_areas': ['cardiac chambers', 'myocardium', 'valves', 'coronary arteries', 'great vessels', 'pericardium'],
                'urgency_indicators': ['acute coronary syndrome', 'aortic dissection', 'pulmonary embolism', 'tamponade'],
            },
            'orthopedic': {
                'focus': 'musculoskeletal system, bone, joint, and soft tissue findings',
                'key_areas': ['bone alignment', 'fractures', 'joint spaces', 'soft tissue', 'ligaments', 'degenerative changes'],
                'urgency_indicators': ['displaced fractures', 'neurovascular compromise', 'compartment syndrome'],
            },
            'pulmonologist': {
                'focus': 'pulmonary and thoracic imaging findings',
                'key_areas': ['lung parenchyma', 'airways', 'pleura', 'mediastinum', 'hilum', 'costophrenic angles'],
                'urgency_indicators': ['pneumothorax', 'massive consolidation', 'pulmonary edema'],
            },
            'neurologist': {
                'focus': 'neuroradiological findings including brain, spinal cord, and neural structures',
                'key_areas': ['gray matter', 'white matter', 'ventricles', 'subarachnoid spaces', 'spinal cord', 'nerves'],
                'urgency_indicators': ['acute stroke', 'brain hemorrhage', 'mass effect', 'cord compression'],
            },
            'gynecologist': {
                'focus': 'gynecological and reproductive imaging findings',
                'key_areas': ['uterus', 'ovaries', 'fallopian tubes', 'adnexa', 'pelvic structures', 'fetal development'],
                'urgency_indicators': ['ectopic pregnancy', 'ovarian torsion', 'obstructed labor'],
            },
            'general_practitioner': {
                'focus': 'general medical imaging findings with differential diagnosis approach',
                'key_areas': ['anatomical structures', 'abnormalities', 'normal variants', 'pathological changes'],
                'urgency_indicators': ['life-threatening conditions', 'acute findings requiring immediate attention'],
            },
        }
        return specialist_contexts.get(specialist_type, specialist_contexts['general_practitioner'])

    def _call_mistral_api(self, image_data, media_type, prompt):
        """Call Mistral Vision API directly via HTTP."""
        if not self.mistral_api_key or not HAS_MISTRAL_API:
            return None

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.mistral_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "max_tokens": 1800,
                "temperature": 0.3,
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('choices') and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
        except Exception:
            pass

        return None

    def analyze_image_specialist_aware(self, filepath, patient_info, specialist_type='general_practitioner'):
        """Advanced image analysis that's specialist-aware and modality-aware."""
        filename = os.path.basename(filepath)

        try:
            image_data = self._encode_image_to_base64(filepath)
            if not image_data:
                return self._fallback_analysis(filename, specialist_type)

            media_type = self._get_image_media_type(filepath)
            modality = self._detect_imaging_modality(filepath, filename, patient_info)
            specialist_context = self._build_specialist_context(specialist_type)

            prompt = self._build_advanced_prompt(
                modality=modality,
                specialist_type=specialist_type,
                specialist_context=specialist_context,
                patient_info=patient_info,
                filename=filename
            )

            result = self._call_mistral_api(image_data, media_type, prompt)
            if result:
                return result
        except Exception:
            pass

        return self._fallback_analysis(filename, specialist_type)

    def _build_advanced_prompt(self, modality, specialist_type, specialist_context, patient_info, filename):
        """Build advanced prompts with deep clinical reasoning and expert analysis."""

        patient_age = patient_info.get('age', 'Not specified')
        patient_gender = patient_info.get('gender', 'Not specified')
        clinical_indication = patient_info.get('indication', patient_info.get('symptoms', 'Not specified'))

        base_system = f"""You are an expert {specialist_type.replace('_', ' ')} AI imaging analyst specializing in {specialist_context['focus']}.

ANALYSIS MANDATE:
- Provide detailed, evidence-based clinical interpretation
- Focus on: {', '.join(specialist_context['key_areas'])}
- For each finding, explain the clinical significance
- Always consider age and gender-specific findings
- Identify patterns that suggest specific diagnoses

CONFIDENCE LEVELS:
- HIGH: Fits the clinical picture well, multiple supporting findings
- MODERATE: Reasonable consideration, needs confirmation
- LOW: Less likely but should be considered, especially if serious

SAFETY REQUIREMENTS:
- NEVER provide definitive diagnoses — use "suggestive of," "consistent with," "consider"
- ALWAYS flag urgency indicators: {', '.join(specialist_context['urgency_indicators'])}
- ALWAYS recommend professional radiologist/{specialist_type.replace('_', ' ').title()} review
- This analysis supports clinical decision-making — NOT a replacement for professional evaluation"""

        if modality == 'ct':
            prompt = f"""{base_system}

IMAGING MODALITY: CT (Computed Tomography)
Image: {filename}
Patient: Age {patient_age} | Gender {patient_gender}
Clinical Indication: {clinical_indication}

Provide a systematic CT analysis covering:
1. TECHNICAL QUALITY — Image quality and any artifacts affecting interpretation
2. SYSTEMATIC SURVEY — Organ-by-organ evaluation, noting normal and abnormal findings
3. ABNORMALITY CHARACTERIZATION — For each finding: location, size, density, margins, clinical significance
4. DIFFERENTIAL DIAGNOSIS — Top 3-5 possibilities with confidence levels and reasoning
5. RED FLAGS — Any critical findings requiring immediate attention
6. RECOMMENDATIONS — Additional imaging, clinical correlation needed, follow-up timing

Show your clinical reasoning — explain WHY findings suggest specific diagnoses.
CRITICAL: Professional radiologist review is REQUIRED for diagnosis."""

        elif modality == 'mri':
            prompt = f"""{base_system}

IMAGING MODALITY: MRI (Magnetic Resonance Imaging)
Image: {filename}
Patient: Age {patient_age} | Gender {patient_gender}
Clinical Indication: {clinical_indication}

Provide a systematic MRI analysis covering:
1. SEQUENCE IDENTIFICATION — Available sequences (T1, T2, FLAIR, DWI, etc.) and image quality
2. SIGNAL ANALYSIS — For each abnormality: signal characteristics on each sequence and what they indicate
3. ANATOMICAL LOCALIZATION — Precise location, size, relationship to critical structures, mass effect
4. ENHANCEMENT PATTERN — If contrast used: enhancement pattern and pathological implications
5. DIFFERENTIAL DIAGNOSIS — Top 3-5 possibilities with confidence levels, explaining MRI features supporting each
6. CRITICAL FINDINGS — Any urgent findings (acute stroke, hemorrhage, cord compression)
7. RECOMMENDATIONS — Additional sequences, clinical correlation, follow-up

Explain what signal patterns MEAN pathophysiologically.
CRITICAL: Professional MRI interpretation REQUIRED for diagnosis."""

        elif modality == 'xray':
            prompt = f"""{base_system}

IMAGING MODALITY: X-Ray (Radiograph)
Image: {filename}
Patient: Age {patient_age} | Gender {patient_gender}
Clinical Indication: {clinical_indication}

Provide a systematic X-ray analysis covering:
1. TECHNICAL QUALITY — Exposure, positioning, any limitations
2. SYSTEMATIC EVALUATION — Evaluate each visible structure methodically
3. ABNORMALITY CHARACTERIZATION — For each finding: exact location, description, clinical significance
4. BONE & JOINT ASSESSMENT — Alignment, fractures, joint spaces, degenerative changes
5. SOFT TISSUE EVALUATION — Swelling, calcification, foreign bodies
6. DIFFERENTIAL DIAGNOSIS — Top 3-5 possibilities with radiographic features supporting each
7. RED FLAGS — Displaced fractures, pneumothorax, other urgent findings
8. RECOMMENDATIONS — Additional views, advanced imaging, clinical correlation

Be specific with anatomical terminology and explain radiographic-pathological correlations.
CRITICAL: Professional radiologist review REQUIRED for diagnosis."""

        elif modality == 'ultrasound':
            prompt = f"""{base_system}

IMAGING MODALITY: Ultrasound (Sonography)
Image: {filename}
Patient: Age {patient_age} | Gender {patient_gender}
Clinical Indication: {clinical_indication}

Provide a systematic ultrasound analysis covering:
1. TECHNICAL FACTORS — Acoustic window quality, artifacts, limitations
2. ANATOMICAL SURVEY — Region-by-region evaluation, normal and abnormal findings
3. LESION CHARACTERIZATION — Echotexture, echogenicity, margins, size, internal characteristics (cystic vs solid)
4. DOPPLER FINDINGS — If applicable: flow characteristics, resistance indices
5. DIFFERENTIAL DIAGNOSIS — Top 3-5 possibilities with confidence levels, ultrasound features supporting each
6. RED FLAGS — Critical findings (free fluid, thrombosis, obstruction)
7. RECOMMENDATIONS — Additional views, advanced imaging, clinical correlation

Acknowledge operator-dependency and explain what echotexture patterns indicate.
CRITICAL: Professional interpretation with clinical correlation REQUIRED."""

        else:
            prompt = f"""{base_system}

MEDICAL IMAGE ANALYSIS
Image: {filename}
Patient: Age {patient_age} | Gender {patient_gender}
Clinical Indication: {clinical_indication}

Provide a comprehensive analysis covering:
1. IMAGE ASSESSMENT — Technical quality, modality identification, limitations
2. SYSTEMATIC SURVEY — Organized anatomical evaluation, normal and abnormal findings
3. ABNORMALITY CHARACTERIZATION — Morphology, density/signal, location, margins, significance
4. DIFFERENTIAL DIAGNOSIS — Top 3-5 possibilities with confidence levels and reasoning
5. RED FLAGS — Any emergent or critical findings
6. INCIDENTAL FINDINGS — Unrelated findings that may need follow-up
7. RECOMMENDATIONS — Additional imaging, clinical correlation, specialist referral

Show your clinical thinking — explain what you see and WHY it matters.
CRITICAL: Professional imaging interpretation recommended for definitive diagnosis."""

        return prompt

    def analyze_skin_condition(self, filepath, patient_info):
        """Legacy method — now uses advanced specialist-aware analysis."""
        return self.analyze_image_specialist_aware(filepath, patient_info, 'dermatologist')

    def analyze_xray(self, filepath, patient_info):
        """Legacy method — now uses advanced specialist-aware analysis."""
        return self.analyze_image_specialist_aware(filepath, patient_info, 'general_practitioner')

    def _fallback_analysis(self, filename, specialist_type='general_practitioner'):
        """Enhanced fallback response with specialist context."""
        return (
            f"📋 **Image Review: {filename}**\n\n"
            f"**Status**: The vision analysis service is currently unavailable.\n\n"
            "**What you can do**:\n"
            "- Verify MISTRAL_API_KEY environment variable is correctly set\n"
            "- Check internet connection and API status\n"
            "- Ensure image format is supported (JPEG, PNG, GIF, WebP)\n\n"
            f"**Recommended Action**:\n"
            f"- Consult a qualified {specialist_type.replace('_', ' ')} with this image\n"
            f"- Provide clinical context along with the image\n"
            f"- Request formal imaging interpretation\n\n"
            "**Important**: This is NOT a medical diagnosis. Professional evaluation is required."
        )

    def _fallback_skin_analysis(self, filename):
        """Legacy fallback — redirects to generic fallback."""
        return self._fallback_analysis(filename, 'dermatologist')

    def _fallback_xray_analysis(self, filename):
        """Legacy fallback — redirects to generic fallback."""
        return self._fallback_analysis(filename, 'general_practitioner')


class MedicalRAGPipeline:
    def __init__(self, api_key=None, collection_name="medical_docs"):
        self.api_key = api_key
        self.collection_name = collection_name
        self.documents = {}
        self.model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.client = None
        if Groq and api_key:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.client = None

    _SPECIALIST_FOCUS_TERMS = {
        "neurologist": ["headache", "seizure", "stroke", "weakness", "numbness", "brain", "spine"],
        "cardiologist": ["chest", "ecg", "troponin", "cardiac", "heart", "bp", "stent"],
        "orthopedic": ["fracture", "joint", "bone", "ligament", "tendon", "spine", "arthritis"],
        "general_practitioner": ["fever", "infection", "pain", "fatigue", "blood", "inflammation"],
        "pulmonologist": ["cough", "asthma", "lung", "spo2", "breath", "pneumonia", "pleural"],
        "dentist": ["tooth", "gum", "oral", "jaw", "dental", "caries", "abscess"],
        "dermatologist": ["rash", "lesion", "itch", "skin", "pigment", "mole", "erythema"],
        "gynecologist": ["pelvic", "uterus", "ovary", "menstrual", "vaginal", "pregnancy", "fibroid"],
    }

    def _chunk_text(self, text: str, max_words: int = 220, overlap_words: int = 45) -> List[str]:
        words = text.split()
        if not words:
            return []
        if len(words) <= max_words:
            return [" ".join(words)]

        chunks = []
        start = 0
        total_words = len(words)
        while start < total_words:
            end = min(total_words, start + max_words)
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end >= total_words:
                break
            start = max(start + 1, end - overlap_words)
        return chunks

    def _extract_terms(self, text: str) -> List[str]:
        if not text:
            return []
        return [term for term in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(term) >= 3]

    def _build_weighted_terms(self, question: str, specialist_type: str, patient_info: Optional[Dict]) -> Dict[str, float]:
        weighted_terms: Dict[str, float] = {}

        for term in self._extract_terms(question):
            weighted_terms[term] = max(weighted_terms.get(term, 0), 3.0)

        for term in self._SPECIALIST_FOCUS_TERMS.get(specialist_type, []):
            weighted_terms[term] = max(weighted_terms.get(term, 0), 2.0)

        if isinstance(patient_info, dict):
            for value in patient_info.values():
                if not value:
                    continue
                for term in self._extract_terms(str(value)):
                    weighted_terms[term] = max(weighted_terms.get(term, 0), 1.5)

        return weighted_terms

    def _score_chunk(self, chunk: str, weighted_terms: Dict[str, float]) -> float:
        chunk_lower = chunk.lower()
        score = 0.0
        term_hits = 0

        for term, weight in weighted_terms.items():
            if term in chunk_lower:
                score += weight
                term_hits += 1

        if term_hits:
            score += min(term_hits, 6) * 0.25

        return score

    def _get_doc_text_and_chunks(self, doc_data) -> Tuple[str, List[str]]:
        if isinstance(doc_data, dict):
            text = str(doc_data.get("text", "")).strip()
            chunks = doc_data.get("chunks") or []
            if not isinstance(chunks, list):
                chunks = []
            cleaned_chunks = [str(chunk).strip() for chunk in chunks if str(chunk).strip()]
        else:
            text = str(doc_data or "").strip()
            cleaned_chunks = []

        if not cleaned_chunks and text:
            cleaned_chunks = self._chunk_text(text)

        return text, cleaned_chunks

    def _iter_documents(self, document_ids: Optional[List[str]] = None):
        if not document_ids:
            for item in self.documents.items():
                yield item
            return

        allowed_ids = set(document_ids)
        for doc_id, doc_data in self.documents.items():
            if doc_id in allowed_ids:
                yield doc_id, doc_data

    def _retrieve_top_chunks(
        self,
        question: str,
        specialist_type: str,
        patient_info: Optional[Dict],
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
    ):
        weighted_terms = self._build_weighted_terms(question, specialist_type, patient_info)
        scored_chunks = []

        for doc_id, doc_data in self._iter_documents(document_ids):
            text, chunks = self._get_doc_text_and_chunks(doc_data)
            if not chunks and text:
                chunks = [text[:1600]]

            for idx, chunk in enumerate(chunks, start=1):
                score = self._score_chunk(chunk, weighted_terms)
                if score > 0:
                    scored_chunks.append((score, doc_id, idx, chunk))

        if not scored_chunks:
            fallback_chunks = []
            for doc_id, doc_data in self._iter_documents(document_ids):
                _, chunks = self._get_doc_text_and_chunks(doc_data)
                for idx, chunk in enumerate(chunks[:2], start=1):
                    fallback_chunks.append((0.1, doc_id, idx, chunk))
                    if len(fallback_chunks) >= top_k:
                        return fallback_chunks
            return fallback_chunks

        scored_chunks.sort(key=lambda item: item[0], reverse=True)
        selected = []
        seen = set()
        for chunk_data in scored_chunks:
            key = (chunk_data[1], chunk_data[2])
            if key in seen:
                continue
            seen.add(key)
            selected.append(chunk_data)
            if len(selected) >= top_k:
                break

        return selected

    def _build_patient_context(self, patient_info: Optional[Dict]) -> str:
        if not isinstance(patient_info, dict):
            return "Not provided"

        lines = []
        for key, value in patient_info.items():
            if value is None:
                continue
            value_text = str(value).strip()
            if not value_text:
                continue
            if value_text.lower() in {"not specified", "unknown", "none"}:
                continue
            lines.append(f"- {key.replace('_', ' ').title()}: {value_text}")

        return "\n".join(lines) if lines else "Not provided"

    def _build_evidence_block(self, top_chunks) -> str:
        lines = []
        for score, doc_id, chunk_idx, chunk in top_chunks:
            normalized = " ".join(chunk.split())
            if len(normalized) > 850:
                normalized = normalized[:850].rsplit(" ", 1)[0] + "..."
            lines.append(f"[Source: {doc_id} | Chunk: {chunk_idx} | Relevance: {score:.2f}]")
            lines.append(normalized)
            lines.append("")
        return "\n".join(lines).strip()

    def _query_with_groq(self, question: str, specialist_type: str, patient_info: Optional[Dict], evidence_block: str) -> Optional[str]:
        if not self.client:
            return None

        specialist_name = specialist_type.replace("_", " ").title()
        specialist_rules = SPECIALIST_PROMPTS.get(specialist_type, SPECIALIST_PROMPTS["general_practitioner"])

        system_prompt = (
            f"You are an expert {specialist_name} clinical document analyst. "
            "Answer ONLY using the provided PDF evidence. "
            "If details are missing, explicitly write 'Not found in uploaded PDF evidence'. "
            "Never provide a definitive diagnosis. Always use cautious medical language. "
            "Cite sources in this format: [Source: document_id]. "
            "Use this exact structure:\n"
            "1. Key Findings From PDF\n"
            "2. Specialist Interpretation\n"
            "3. Recommended Next Steps\n"
            "4. Safety Note"
        )

        user_prompt = (
            f"Patient question:\n{question}\n\n"
            f"Specialist: {specialist_name}\n\n"
            f"Patient context:\n{self._build_patient_context(patient_info)}\n\n"
            f"Specialist reasoning guidance:\n{specialist_rules}\n\n"
            f"PDF evidence snippets:\n{evidence_block}\n\n"
            "Respond now."
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=1100,
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception:
            return None

        return None

    def process_pdf(self, filepath, document_id=None):
        if PdfReader is None:
            raise RuntimeError("pypdf is not available in this environment")

        reader = PdfReader(filepath)
        text_parts = []
        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                normalized_text = " ".join(text.split())
                text_parts.append(f"[Page {page_idx}] {normalized_text}")

        combined_text = "\n".join(text_parts).strip()
        if not combined_text:
            combined_text = "No extractable text found in PDF. The file may be scanned or image-only."

        doc_id = document_id or os.path.basename(filepath)
        self.documents[doc_id] = {
            "text": combined_text,
            "chunks": self._chunk_text(combined_text),
        }

        return {
            "document_id": doc_id,
            "characters_indexed": len(combined_text),
        }

    def query_documents(self, question, patient_info=None, specialist_type="general_practitioner", document_ids=None):
        if not self.documents:
            return "No uploaded medical documents are available to query yet."

        if not question or not question.strip():
            question = "Provide a concise summary of the uploaded medical report."

        top_chunks = self._retrieve_top_chunks(
            question=question,
            specialist_type=specialist_type,
            patient_info=patient_info,
            document_ids=document_ids,
            top_k=5,
        )

        if not top_chunks:
            return "I reviewed the uploaded document, but I could not extract relevant clinical evidence for this question."

        evidence_block = self._build_evidence_block(top_chunks)

        llm_response = self._query_with_groq(
            question=question,
            specialist_type=specialist_type,
            patient_info=patient_info,
            evidence_block=evidence_block,
        )
        if llm_response:
            return llm_response

        lines = ["Based on uploaded medical documents, here are the most relevant evidence snippets:"]
        for _, doc_id, chunk_idx, chunk in top_chunks:
            snippet = " ".join(chunk.split())
            if len(snippet) > 280:
                snippet = snippet[:280].rsplit(" ", 1)[0] + "..."
            lines.append(f"- [Source: {doc_id}, chunk {chunk_idx}] {snippet}")
        lines.append("")
        lines.append("Note: Configure GROQ_API_KEY for deeper specialist-level PDF reasoning.")
        return "\n".join(lines)

    def delete_collection(self):
        self.documents.clear()