# Vessel Charter Recommendation API

FastAPI wrapper for the supplied vessel/charter-month model. The endpoint accepts the request-specific values that were hard-coded in the notebook and returns ranked recommendations as JSON.

## Required data

Place these six CSVs in `backend/data/` for a local run and include them in the Docker image for the simplest Koyeb deployment:

- `vessels.csv`
- `ports.csv`
- `freight_rates.csv`
- `market_indicators.csv`
- `route_distances.csv`
- `cargo_orders.csv`

Keep the column names and units expected by the original model. Do not commit private or licensed data to a public repository. For larger or sensitive files, store them in object storage and download them at container startup, or use a persistent volume; the application supports `DATA_DIR` for a mounted data folder. Koyeb's ordinary container filesystem is ephemeral, so a model cache written at runtime is not durable across replacement/redeployments. Model training happens on the first recommendation request and can take time; the generated cache is reused while the container remains alive.

## Run locally

From `backend/`:

```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs`. `GET /health` reports which CSVs are present. `POST /api/recommendations` accepts:

```json
{
  "origin_port": "Gladstone",
  "destination_port": "Paradip",
  "quantity": 6767,
  "type_of_cargo": "coal",
  "expected_arrival": "2027-11-11"
}
```

Optional fields are `run_date` (`YYYY-MM-DD`) and `force_retrain` (boolean). `quantity` is passed through as-is; ensure its unit matches the DWT and training/data assumptions in the model. A successful response has `count` and a `recommendations` array.

## Deploy to Koyeb

1. Put this `backend/` directory in a Git repository and push it to GitHub. Add the six CSVs under `backend/data/` only if the repository is private and you are permitted to store them there. Keep `.env` and model cache files out of Git.
2. In Koyeb, create an App and choose **Deploy from GitHub**. Select the repository and branch.
3. Set the service **Work directory** to `backend` and choose **Dockerfile** as the builder (Dockerfile path `Dockerfile`). If the Koyeb form expects a repository-relative path, use `backend/Dockerfile` and leave work directory unset instead.
4. Set the service port to `8000` (HTTP). Koyeb injects `PORT`; the Docker command listens on it.
5. Add `CORS_ORIGINS` as a comma-separated list of your deployed frontend origins, for example `https://your-site.example`. For local frontend work use `http://localhost:3000,http://localhost:5173`. Avoid `*` when credentials are in use; this API does not enable credentialed CORS.
6. Deploy, then open `https://<your-service-domain>/health`. It should say `status: ok` and show all six files as `true`. Visit `/docs` to try the endpoint.
7. In Bolt/Lovable/Figma-generated frontend code, set its API base URL to the Koyeb service URL and POST JSON to `/api/recommendations`. The browser origin must be listed in `CORS_ORIGINS`; redeploy after changing environment variables.

## Model behavior to review before launch

The supplied script uses synthetic market indicators and synthetic lag/reference rates seeded with 42 for inference. Those are preserved here to retain the supplied behavior, but recommendations therefore are not driven by live market values. The existing model's `quantity_kg = quantity` assignment and freight cost multiplication by vessel DWT are also unchanged; validate units and cost assumptions against your project data before presenting costs as operational quotes.
