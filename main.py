import json
import os
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import recommender

app = FastAPI(
    title="Vessel Charter Recommendation API",
    description="Ranks vessels and follow-on Indian port orders by estimated total cost.",
    version="1.0.0",
)

origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RecommendationRequest(BaseModel):
    origin_port: str = Field(min_length=1, examples=["Gladstone"])
    destination_port: str = Field(min_length=1, examples=["Paradip"])
    quantity: float = Field(gt=0, description="Cargo quantity in the same units as the model's vessel DWT data")
    type_of_cargo: str = Field(min_length=1, examples=["coal"])
    expected_arrival: date
    run_date: date | None = Field(default=None, description="Deprecated; forecast months are anchored to the latest month in freight-rate data")
    force_retrain: bool = False


@app.get("/")
def root():
    return {"service": "vessel-charter-recommendation-api", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    required = ["vessels.csv", "ports.csv", "freight_rates.csv", "market_indicators.csv", "route_distances.csv", "cargo_orders.csv"]
    data_dir = recommender.resolve_data_dir()
    present = {name: os.path.isfile(os.path.join(data_dir, name)) for name in required}
    return {"status": "ok" if all(present.values()) else "needs_data", "data_dir": data_dir, "files": present}


@app.post("/api/recommendations")
def recommendations(request: RecommendationRequest):
    try:
        result = recommender.recommend(
            origin_port=request.origin_port,
            destination_port=request.destination_port,
            quantity=request.quantity,
            type_of_cargo=request.type_of_cargo,
            expected_arrival=request.expected_arrival.isoformat(),
            run_date=request.run_date.isoformat() if request.run_date else None,
            force_retrain=request.force_retrain,
        )
        return {"count": len(result), "recommendations": json.loads(result.to_json(orient="records", date_format="iso"))}
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Keep internal stack traces out of the public API response.
        raise HTTPException(status_code=500, detail="Recommendation failed. Check deployment logs and input data.") from exc
