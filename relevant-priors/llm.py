# llm.py
# Uses Claude API to predict relevance for cases that rules can't handle well.
# Key design: one API call per case (batch all priors together) to avoid timeout.

import anthropic
import json
import os

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def predict_relevance_with_llm(current_description: str, prior_studies: list) -> dict:
    """
    Sends one batched request to Claude for all priors of a single case.
    
    Returns a dict: {study_id -> bool}
    
    Example:
        predict_relevance_with_llm(
            "MRI BRAIN STROKE",
            [{"study_id": "123", "study_description": "CT HEAD"}]
        )
        -> {"123": True}
    """

    # Format the prior studies for the prompt
    priors_text = "\n".join([
        f"- study_id: {p['study_id']} | description: {p['study_description']}"
        for p in prior_studies
    ])

    prompt = f"""You are a radiologist assistant. 
    
Current study: {current_description}

For each prior study below, decide if a radiologist reading the current study 
would find it useful to see. Consider whether they cover the same or closely 
related anatomical region.

Prior studies:
{priors_text}

Return ONLY a JSON array, no explanation, no markdown. Example format:
[{{"study_id": "123", "is_relevant": true}}, {{"study_id": "456", "is_relevant": false}}]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        results = json.loads(raw)

        # Convert list to dict for easy lookup
        return {r["study_id"]: r["is_relevant"] for r in results}

    except Exception as e:
        print(f"LLM error: {e}")
        # If LLM fails, return empty dict -> caller will fall back to rules
        return {}