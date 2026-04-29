# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from rules import is_relevant
from llm import predict_relevance_with_llm
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request models
class Study(BaseModel):
    study_id: str
    study_description: str
    study_date: str

class Case(BaseModel):
    case_id: str
    patient_id: str
    patient_name: str
    current_study: Study
    prior_studies: List[Study]

class PredictRequest(BaseModel):
    challenge_id: str
    schema_version: int
    generated_at: str
    cases: List[Case]

# Response models
class Prediction(BaseModel):
    case_id: str
    study_id: str
    predicted_is_relevant: bool

class PredictResponse(BaseModel):
    predictions: List[Prediction]


# App

app = FastAPI(title="Relevant Priors API")

# Check if LLM is available (API key set)
USE_LLM = os.environ.get("ANTHROPIC_API_KEY") is not None
logger.info(f"LLM enabled: {USE_LLM}")

@app.get("/")
def health_check():
    return {"status": "ok", "llm_enabled": USE_LLM}

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    total_priors = sum(len(c.prior_studies) for c in request.cases)
    logger.info(
        f"Request received | cases={len(request.cases)} | priors={total_priors} | llm={USE_LLM}"
    )

    predictions = []

    for case in request.cases:
        current_desc = case.current_study.study_description
        prior_list = [
            {"study_id": p.study_id, "study_description": p.study_description}
            for p in case.prior_studies
        ]

        # Step 1: Run rules on all priors
        rule_results = {
            p.study_id: is_relevant(current_desc, p.study_description)
            for p in case.prior_studies
        }

        # Step 2: Find uncertain priors (where rules returned False)
        # These are candidates for LLM review
        uncertain_priors = [
            p for p in prior_list
            if not rule_results[p["study_id"]]
        ]

        # Step 3: Ask LLM about uncertain priors in one batched call
        llm_results = {}
        if USE_LLM and uncertain_priors:
            llm_results = predict_relevance_with_llm(current_desc, uncertain_priors)
            logger.info(f"  case={case.case_id} | uncertain={len(uncertain_priors)} | llm_results={llm_results}")

        # Step 4: Merge results — rules win on True, LLM fills in the rest
        for prior in case.prior_studies:
            if rule_results[prior.study_id]:
                # Rules said True -> trust it
                final = True
            elif prior.study_id in llm_results:
                # Rules said False but LLM has an opinion -> use LLM
                final = llm_results[prior.study_id]
            else:
                # No LLM result -> fall back to rules (False)
                final = rule_results[prior.study_id]

            predictions.append(Prediction(
                case_id=case.case_id,
                study_id=prior.study_id,
                predicted_is_relevant=final,
            ))

    logger.info(f"Returning {len(predictions)} predictions")
    return PredictResponse(predictions=predictions)