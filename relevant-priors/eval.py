# eval.py
import json
from rules import is_relevant
from llm import predict_relevance_with_llm
import os

USE_LLM = os.environ.get("ANTHROPIC_API_KEY") is not None
print(f"LLM enabled: {USE_LLM}")

with open("relevant_priors_public.json", "r") as f:
    data = json.load(f)

truth_lookup = {}
for t in data["truth"]:
    key = (t["case_id"], t["study_id"])
    truth_lookup[key] = t["is_relevant_to_current"]

correct = 0
incorrect = 0
wrong_predictions = []

for i, case in enumerate(data["cases"][:50]):
    current_desc = case["current_study"]["study_description"]

    # Step 1: run rules on all priors
    rule_results = {
        p["study_id"]: is_relevant(current_desc, p["study_description"])
        for p in case["prior_studies"]
    }

    # Step 2: find uncertain priors (rules said False)
    uncertain_priors = [
        p for p in case["prior_studies"]
        if not rule_results[p["study_id"]]
    ]

    # Step 3: ask LLM about uncertain priors
    llm_results = {}
    if USE_LLM and uncertain_priors:
        llm_results = predict_relevance_with_llm(
            current_desc, uncertain_priors
        )

    # Step 4: merge and evaluate
    for prior in case["prior_studies"]:
        key = (case["case_id"], prior["study_id"])
        label = truth_lookup.get(key)
        if label is None:
            continue

        if rule_results[prior["study_id"]]:
            final = True
        elif prior["study_id"] in llm_results:
            final = llm_results[prior["study_id"]]
        else:
            final = False

        if final == label:
            correct += 1
        else:
            incorrect += 1
            wrong_predictions.append({
                "current": current_desc,
                "prior": prior["study_description"],
                "label": label,
                "predicted": final,
            })

    if (i + 1) % 100 == 0:
        print(f"Progress: {i+1}/{len(data['cases'])} cases done...")

total = correct + incorrect
accuracy = correct / total * 100

print(f"\nTotal predictions : {total}")
print(f"Correct           : {correct}")
print(f"Incorrect         : {incorrect}")
print(f"Accuracy          : {accuracy:.2f}%")

print("\n--- First 10 wrong predictions ---")
for w in wrong_predictions[:10]:
    print(f"  current  : {w['current']}")
    print(f"  prior    : {w['prior']}")
    print(f"  label={w['label']} | predicted={w['predicted']}")
    print()