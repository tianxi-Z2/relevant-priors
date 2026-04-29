# Experiments & Write-up

## Problem Summary

Given a current radiology study and a list of prior studies for the same patient,
predict whether each prior study is relevant for the radiologist reading the current one.

Only `study_description` and `study_date` are available — no report text, no images.

---

## Approach 1: Rule-Based Body Part Matching

### Idea
Parse the `study_description` string to extract the anatomical region,
then predict relevant = True if current and prior share the same region.

### Implementation
- Defined 15+ body part groups (HEAD, CHEST, BREAST, SPINE, etc.)
- Each group has a list of keywords matched against the uppercased description
- Priority groups (ABD_PELVIS, WHOLE_BODY) are checked first to avoid false matches

### Iteration History

| Version | Change | Accuracy |
|---------|--------|----------|
| v1 | Initial keyword groups | 83.87% |
| v2 | Added MAM/MAMMOGRAPH to CHEST | 84.92% |
| v3 | Separated BREAST from CHEST as its own group | 91.28% |
| v4 | Added ULTRASOUND BILAT, MAM US to BREAST group | 91.33% |

### Key Insight
Mammography (MAM) and chest CT are treated as **different** by radiologists
even though both involve the chest area. Separating them into distinct groups
was the single biggest accuracy improvement (+6%).

---

## Approach 2: Rule-Based + LLM Hybrid

### Idea
Rules handle clear-cut cases. For priors that rules predict as False,
ask Claude to make the final call — all priors for one case in a single batched API call.

### Why Batching Matters
The evaluator times out after 360 seconds with 996 cases and 27,614 priors.
One LLM call per prior would be ~27,000 API calls — guaranteed timeout.
One LLM call per case = ~996 calls, well within the time budget.

### Implementation
- Rules run first on all priors
- Only priors where rules returned False are sent to LLM
- LLM receives the current description + all uncertain priors in one prompt
- Results are merged: rules win on True, LLM fills in uncertain cases

### Results (50-case sample)
| Method | Accuracy |
|--------|----------|
| Rules only | 91.33% |
| Rules + LLM | 93.88% |

LLM improved accuracy by ~2.5% by catching edge cases rules missed,
such as cardiac SPECT vs coronary CT (same anatomical focus, different modality names).

---

## What Worked
- Separating BREAST from CHEST was the biggest single gain
- Batching all priors per case into one LLM call solved the timeout problem
- Using rules as a first filter reduced LLM calls by ~60%, saving cost and latency

## What Did Not Work
- LLM sometimes over-predicted True for thoracic spine vs chest CT
- JSON parsing errors when LLM output exceeded token limits
- Left/right side disambiguation (MAM RT vs MAM LT) is hard for both rules and LLM

---

## Next Steps

1. **Smarter LLM routing** — only send to LLM when both descriptions have no matching group,
   not just when rules return False. This prevents LLM from overriding correct rule predictions.

2. **Fine-grained laterality rules** — detect Left/Right keywords to avoid
   predicting MAM RT as relevant to MAM LT.

3. **Caching** — cache LLM results by (current_description, prior_description) pair
   so repeated study pairs don't trigger redundant API calls.

4. **Confidence scoring** — instead of binary True/False, have LLM return
   a confidence score and tune the threshold on the public eval set.

5. **Study date weighting** — more recent priors are likely more relevant;
   incorporate time delta as a feature.
