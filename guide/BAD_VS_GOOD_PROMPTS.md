# 🔄 Bad vs. Good Patient Prompts - Side-by-Side Comparison

## SCENARIO 1: Chest Pain (Cardiologist)

### ❌ BAD PROMPT (Generic/Vague)
```
"I have chest pain for a few days. It really hurts. 
My dad had heart problems. 
Should I go to the hospital? 
I'm on some medication but I'm not sure which ones. 
I'm really scared. What's wrong with me?"

Length: 50 words
Specificity: Very low
Actionability: Impossible to analyze
```

**AI Response**:
```
"Chest pain can have many causes and requires professional evaluation. 
Risk factors include family history of heart disease. 
You should see a doctor or go to the ER if you have severe symptoms. 
Please seek immediate medical attention."
```
❌ **Problem**: Generic, not helpful, no differential diagnosis

---

### ✅ GOOD PROMPT (Specific/Detailed)
```
"I'm a 58-year-old male. For 3 days, I've had intermittent chest pressure - 
around 6/10 severity, located in the center of my chest radiating to my left arm.

TRIGGERS/PATTERN:
- Happens with exertion (climbing stairs, walking uphill, cold air)
- Lasts 5-10 minutes
- Goes away with rest
- Happens about 2-3 times daily

ASSOCIATED:
- Mild shortness of breath during episodes
- Occasional sweating
- Fatigue
- No nausea, no vomiting

MEDICAL HISTORY:
- High blood pressure 10 years (on treatment)
- High cholesterol 5 years (on treatment)
- Family: Father had MI at 62 (I'm now 58 - same age!)
- Quit smoking 3 years ago (20 pack-year history)
- Very sedentary job

MEDICATIONS:
- Metoprolol 50mg daily
- Atorvastatin 20mg daily

TESTING:
- Got EKG yesterday - doctor said 'borderline finding'
- [EKG image attached]

MY CONCERN: Terrified about unstable angina or impending MI

SPECIFIC QUESTIONS:
1) Based on my symptoms/EKG, what's the top differential?
2) How urgent is this - do I need immediate cardiology workup?
3) Which tests (stress test, coronary CT, angiography)?
4) What's my risk level based on all factors?"

Length: 300+ words
Specificity: Very high
Actionability: Clear analysis possible
```

**AI Response**:
```
"CARDIAC ANALYSIS:

CLINICAL PRESENTATION:
Your typical exertional chest pressure with relief at rest is classic for 
angina pectoris. The radiation to left arm is concerning for cardiac origin.

DIFFERENTIAL DIAGNOSIS:
1. [HIGH CONFIDENCE] Stable angina with underlying coronary atherosclerotic 
   disease
   - Supporting: Exertional trigger, relief with rest, risk factors (age, 
     HTN, high chol, former smoker, sedentary)
   - Your age + father's MI at 62 = significant risk
   
2. [MODERATE CONFIDENCE] Unstable angina
   - Supporting: Increasing frequency (new onset 3 days ago)
   - Risk: More unpredictable if worsening pattern
   
3. [LOW CONFIDENCE] Non-cardiac (musculoskeletal)
   - Against: Exertional pattern, radiation to arm, associated SOB

BORDERLINE EKG CONSIDERATION:
- Borderline EKG + typical exertional chest pain = positive predictive value 
  for underlying CAD
- Need risk stratification with stress testing or coronary imaging

RECOMMENDED NEXT STEPS (URGENCY: High):
1. Cardiology referral - URGENT (not routine appointment)
2. Stress test or coronary CT angiography within 24-48 hours
3. If symptoms worsen or occur at rest = go to ER immediately

RED FLAGS requiring ER:
- Chest pain at rest or with minimal exertion
- Pain unrelieved by rest
- Pain with new symptoms (severe SOB, syncope, diaphoresis)

MANAGEMENT:
- Avoid strenuous activity until evaluated
- Stress management
- Medication optimization (may need additional beta-blocker or nitrate)

BOTTOM LINE: You need urgent cardiac workup. Don't delay."
```
✅ **Result**: Specific differential with confidence levels, clear urgency, actionable next steps

---

## SCENARIO 2: Skin Lesion (Dermatologist)

### ❌ BAD PROMPT (Generic)
```
"I have a mole on my back. It looks weird. 
I'm worried about skin cancer. 
My brother had skin cancer once. 
Is this cancer? What should I do?"

Length: 40 words
Specificity: Almost none
Actionability: Impossible
```

**AI Response**:
```
"Any concerning mole should be evaluated by a dermatologist. 
Signs of melanoma include asymmetry, irregular borders, multiple colors, 
and large size. I cannot diagnose from text. Please see a dermatologist 
for professional evaluation."
```
❌ **Problem**: Completely unhelpful, no specific assessment

---

### ✅ GOOD PROMPT (Specific)
```
"I'm a 50-year-old female. I have a new mole on my back (mid-back, right side) 
that appeared 4 months ago and has been changing.

SIZE PROGRESSION:
- Started: ~5mm (tiny)
- Current: ~9mm (growing in 4 months)
- Growth rate: Clear growth, noticeably bigger every month

APPEARANCE DETAILS:
- Shape: Irregular - not round, asymmetric
- Color: Multiple colors - dark brown, black with tan areas
- Texture: Slightly raised, bumpy surface
- Borders: Uneven/jagged borders, not clean edge

ABCDE CRITERIA ASSESSMENT:
- Asymmetry: YES - one half darker, different than other half
- Border: YES - irregular/jagged borders
- Color: YES - multiple colors present
- Diameter: YES - 9mm (pencil eraser is 6mm, this is larger)
- Evolving: YES - definitely growing and changing

SYMPTOMS:
- Itching: Yes, occasionally itches
- Bleeding: No
- Oozing: No
- Spreading: Just this one lesion, localized

RELEVANT HISTORY:
- Prior skin cancer: No personal history
- Family history: Brother had melanoma at age 45 (removed 5 years ago, he's fine)
- Skin type: Fair skin, burns easily
- Sun exposure: LOTS as child/teen (beach kid), worked outdoors 10 years 
  (minimal sunscreen back then)
- Sunburns: Multiple significant sunburns growing up

CURRENT STATUS:
- Changed nothing - just been watching it
- No treatments applied

PHOTOS:
[Close-up photos attached with ruler for scale reference showing 
current size and irregular borders]

MAIN CONCERN: Very worried this could be melanoma

SPECIFIC QUESTIONS:
1) Based on ABCDE criteria and photos, is this melanoma or concerning for melanoma?
2) Do I need biopsy?
3) How urgent is this? Should I get dermatology referral TODAY or can I wait?
4) What's the removal/treatment approach if it's concerning?
5) My brother had melanoma - does that increase my risk?"

Length: 250+ words
Specificity: Excellent (detailed description + photos + ABCDE criteria)
Actionability: High
```

**AI Response**:
```
"DERMATOLOGY ASSESSMENT:

MELANOMA RISK ASSESSMENT:

CONCERNING FEATURES (5/5 POSITIVE):
✓ Asymmetry: Clear asymmetry visible
✓ Border irregularity: Jagged, uneven borders
✓ Color: Multiple colors (dark brown/black/tan)
✓ Diameter: 9mm (exceeds 6mm threshold)
✓ Evolving: Active growth over 4 months

LIKELIHOOD ASSESSMENT:
[HIGH] Concerning for melanoma or atypical nevi (dysplastic mole)
- The combination of ALL 5 ABCDE features is concerning
- Age 50 + fair skin + high sun exposure = risk factors
- Family history (brother's melanoma) = increased risk for familial melanoma

SUPPORTING FEATURES:
- Size >6mm alone warrants evaluation
- Color variation is concerning
- Clear growth/evolution is RED FLAG
- Multiple colors (especially black) increases concern

DIFFERENTIAL DIAGNOSIS:
1. [HIGH] Melanoma or high-grade dysplastic nevus
2. [MODERATE] Atypical mole
3. [LOW] Common benign nevus (unlikely given evolution)

RECOMMENDED ACTION:
URGENCY: HIGH - Dermatology referral THIS WEEK, not months

NEXT STEP OPTIONS:
1. Dermatologist evaluation with potential shave or punch biopsy
2. Full-body skin exam (given history) to check for other concerning lesions
3. If biopsy shows melanoma: Possible excision with margins + staging

RED FLAGS (Go to ER if):
- Rapid growth
- Bleeding/oozing starts
- Spreads to nearby areas
- New symptoms develop

FAMILY HISTORY NOTE:
- Your brother's melanoma + your characteristics = consider genetics consultation
- If melanoma confirmed, genetic testing may be appropriate

BOTTOM LINE:
This requires professional dermatology evaluation URGENTLY. 
The constellation of features is concerning enough to warrant 
professional assessment and likely biopsy. Do not delay."
```
✅ **Result**: Specific risk assessment, clear recommendation for urgency, differential diagnosis

---

## SCENARIO 3: Persistent Cough (Pulmonologist)

### ❌ BAD PROMPT
```
"I've had a cough for a while. It won't go away. 
Should I be worried? My doctor gave me antibiotics but didn't help. 
What could it be? I'm tired all the time."

Length: 40 words
Specificity: Very poor
Actionability: None
```

**AI Response**:
```
"Persistent cough can have many causes including infection, 
allergies, or lung disease. Please see a pulmonologist for 
evaluation and appropriate testing."
```
❌ **Problem**: No useful information

---

### ✅ GOOD PROMPT
```
"I'm a 58-year-old male. I've had a persistent cough for 5 weeks.
Never smoker, worked in factory with dust/chemical exposure until last year.

COUGH CHARACTERISTICS:
- Type: Mostly dry, sometimes brings up clear mucus
- Frequency: Constant, worse at night and in morning
- Triggers: Cold air, exertion make it worse
- Severity: Occasionally makes me cough so hard I can't catch breath
- Duration of each fit: 1-5 minutes usually
- Sputum: Clear mucus, no blood, no color

CONSTITUTIONAL SYMPTOMS:
- Fever: No fever
- Fatigue: Yes, more tired than usual (new)
- Weight loss: No
- Night sweats: No
- Chills: No

RESPIRATORY SYMPTOMS:
- Shortness of breath: Yes, more winded than usual with exertion
  (used to run 3 miles, now winded doing stairs)
- Wheezing: No wheezing that I notice
- Chest pain: No chest pain
- Stridor: No

EXPOSURE HISTORY:
- Occupational: Factory work 20 years, handled industrial chemicals, 
  dust exposure, poor ventilation
- Just quit job last year due to health concerns
- No recent travel
- No sick contacts
- No new pets

PRIOR TREATMENTS:
- Cough syrup: Didn't help
- Antibiotics: 2-week course (diagnosed as bronchitis), no improvement
- Rest: Been resting, no change
- Humidity: Tried humidifier, minimal help

MEDICAL HISTORY:
- No asthma
- No COPD (never smoked)
- No prior lung disease
- No autoimmune diseases
- General health good until this started

MEDICATIONS: None currently

FAMILY HISTORY:
- Father diagnosed with COPD at 65
- No other lung disease in family

TESTING DONE:
- Chest X-ray (report says 'normal')
- Chest CT ordered by PCP (results attached)
- Spirometry: Not done yet

MAIN CONCERNS:
- Worried this could be serious
- Concerned about occupational exposure (chemical/dust exposure risks)
- Worried about lung cancer given occupational history
- Concerned this isn't just 'bronchitis' if it's not improving

SPECIFIC QUESTIONS:
1) What could cause persistent cough + occupational history?
2) Based on chest X-ray and CT, any concerning findings?
3) Should I have spirometry/pulmonary function testing?
4) Could this be COPD, bronchiectasis, ILD, or malignancy?
5) What's my risk level given occupational exposure?
6) What's the next diagnostic step?"

Length: 280+ words
Specificity: Excellent
Actionability: Yes
```

**AI Response**:
```
"PULMONOLOGY ANALYSIS:

CLINICAL PRESENTATION:
Persistent cough 5 weeks + occupational exposure history + only recent 
smoking cessation + dyspnea on exertion = concerning pattern requiring 
comprehensive evaluation in setting of occupational exposure risk.

IMAGING REVIEW:
[Chest X-ray: Normal per report]
[Chest CT: (analysis of actual findings)]
- If clear: Infection less likely, need pulmonary function testing
- If any findings: Specific comment on findings

DIFFERENTIAL DIAGNOSIS:

1. [MODERATE-HIGH] Occupational lung disease (pneumoconiosis, COPD)
   - Supporting: 20-year occupational exposure, just quit, symptoms now
   - Pattern: Cough + dyspnea = classic for occupational exposure
   - Imaging: May have subtle changes

2. [MODERATE] Chronic bronchitis/Post-bronchitis cough
   - Supporting: Initial infection, persisting beyond expected timeframe
   - Against: Should improve with time

3. [MODERATE] COPD (early stage)
   - Supporting: Occupational exposure = COPD risk equivalent to smoking
   - Against: Non-smoker, good health history
   - Note: Occupational exposure can cause COPD even without smoking

4. [LOW-MODERATE] Bronchiectasis
   - Supporting: Persistent productive cough
   - Against: No recurrent infections, normal CXR
   - Assessment: Possible but less likely

5. [LOW] Malignancy/occupational cancer risk
   - Supporting: Occupational exposure history (certain chemicals/dusts 
     are carcinogenic)
   - Against: 5-week timeline brief for cancer; normal CXR/CT
   - Note: Occupational exposure = lung cancer risk even as non-smoker

CRITICAL NEXT STEPS (URGENCY: Moderate):
1. PULMONARY FUNCTION TESTING - MUST DO
   - Spirometry: Assess for obstructive disease
   - DLCO: Assess for diffuse lung disease
   - This is essential to diagnosis

2. Occupational history assessment:
   - Document specific chemicals/dusts
   - Latency patterns
   - Prior coworkers with similar symptoms?

3. High-resolution CT (if not already done):
   - Better for detecting occupational lung disease
   - Rules out malignancy

4. Consider referral to occupational medicine specialist

RED FLAGS to monitor:
- Hemoptysis (coughing blood)
- Rapid progression
- Fever development
- Significant weight loss

MANAGEMENT:
- Avoid further exposure (you've quit, good)
- Annual surveillance for occupational lung disease
- Consider filing occupational claim depending on findings

PROGNOSIS:
- If occupational COPD: Stabilizes after exposure cessation
- If chronic bronchitis: May persist but typically improves
- Depends on specific diagnosis from PFT

BOTTOM LINE:
Need pulmonary function testing urgently to characterize the 
lung disease. Occupational exposure history is significant risk 
factor for serious lung disease. Risk of cancer with exposure 
requires monitoring even without current findings."
```
✅ **Result**: Specific differential weighted by probability, clarity on occupational risk, actionable next steps

---

## THE PATTERN (Works for ANY Condition)

| Element | BAD | GOOD |
|---------|-----|------|
| **Age** | Missing | "58-year-old male" |
| **Duration** | "for a while" | "exactly 5 weeks, started March 15th" |
| **Character** | "cough" | "dry cough, worse night, clear mucus, fits last 1-5 min" |
| **Triggers** | Missing | "worse with cold air and exertion" |
| **Relief** | Missing | "better during day, worse at night" |
| **Associated** | Vague | SOB with exertion, fatigue, no fever, no weight loss |
| **History** | Doesn't mention | "20-year factory exposure, non-smoker, no COPD" |
| **Meds** | Vague | "2-week antibiotic course (didn't help), tried cough syrup" |
| **Testing** | Missing | "CXR normal, CT attached, spirometry not done" |
| **Question** | Too broad | "Based on history and imaging, differential? Need spirometry? Cancer risk?" |

**Result**: Bad = generic nonsense. Good = expert differential diagnosis

---

## QUICK CONVERSION TEMPLATE

### Convert this...
```
"I'm sick. It's been going on for a while. 
I don't know what's wrong. Help me."
```

### ...Into this:
```
"I'm a [AGE]-year-old [GENDER]. 

For [EXACT DAYS/WEEKS], I've had [SPECIFIC SYMPTOM].

My symptoms are:
- [WHAT it feels like]
- [WHERE it is]
- [WHEN it happens]
- [What makes it worse]
- [What makes it better]
- [Other symptoms]

My history:
- Medical: [list]
- Meds: [list]
- Family history: [relevant items]
- Risk factors: [relevant]

Tests done:
[Include results or images]

I'm concerned about: [your worry]

My questions:
1) What could cause this?
2) How urgent?
3) What tests do I need?
4) What's my next step?"
```

---

**REMEMBER**: 

🎯 **Specific prompt = Specific, useful response**
🎯 **Generic prompt = Generic, unhelpful response**
🎯 **Add details = Get expert analysis**
🎯 **Include images = Get image-specific comments**
🎯 **Ask specific questions = Get actionable answers**

**Make the patient prompt EXCELLENT, get EXCELLENT response!**

