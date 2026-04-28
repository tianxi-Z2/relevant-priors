from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from rules import is_relevant
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# these are request model
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


# these are response model

class Prediction(BaseModel):
    case_id: str
    study_id: str
    predicted_is_relevant: bool

class PredictResponse(BaseModel):
    predictions: List[Prediction]

#app
app = FastAPI(title="Relevant Priors API")

@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    total_priors = sum(len(c.prior_studies) for c in request.cases)
    logger.info(
        f"Request received | cases={len(request.cases)} | priors={total_priors}"
    )

    predictions = []

    for case in request.cases:
        current_desc = case.current_study.study_description
        for prior in case.prior_studies:
            relevant = is_relevant(current_desc, prior.study_description)
            predictions.append(Prediction(
                case_id=case.case_id,
                study_id=prior.study_id,
                predicted_is_relevant=relevant,
            ))

    logger.info(f"Returning {len(predictions)} predictions")
    return PredictResponse(predictions=predictions)