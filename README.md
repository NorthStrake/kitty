# Vessel Charter Recommendation API

FastAPI backend for the supplied vessel and charter-month recommender. It accepts request-specific values and returns ranked recommendations as JSON.

## Data files

The Docker image includes these CSVs under `data/`:

- `vessels.csv`
- `ports.csv`
- `freight_rates.csv`
- `market_indicators.csv`
- `route_distances.csv`
- `cargo_orders.csv`

Keep the column names and units expected by the original model. This project repository is private because it contains the data. For larger or more sensitive datasets, move the CSVs to controlled object storage and load them at runtime; set `DATA_DIR` to the mounted/downloaded directory. Cloud Run's writable container filesystem is temporary, so the model cache is not durable across instance replacement. Models train on the first recommendation request and the cache is reused only while that instance remains alive.

## Run locally

From this repository's root:

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

Optional fields are `run_date` (`YYYY-MM-DD`) and `force_retrain` (boolean). `quantity` is passed through as-is; ensure its unit matches the model's DWT and training-data assumptions. A successful response has `count` and a `recommendations` array.

## Deploy to Google Cloud Run

This GitHub repository is rooted at the backend files, with `Dockerfile` at the root.

1. In Google Cloud Console, select or create a project and enable billing. Open **Cloud Run** and choose **Deploy from a repository** / continuous deployment.
2. Connect GitHub through Cloud Build or Developer Connect. Grant access to the private `NorthStrake/kitty` repository, then select branch `main`.
3. For build configuration, choose **Dockerfile** and set the Dockerfile location and build context to the repository root (`Dockerfile` and `.`). Do not set a subdirectory/work directory.
4. Set the service name (for example, `vessel-charter-api`) and choose a region near the expected users. Set **Container port** to `8080`; the Dockerfile listens on Cloud Run's injected `PORT` value.
5. Set **Maximum concurrent requests per instance** to `1` initially because the first recommendation request trains the models and can use substantial CPU. Use at least **2 GiB memory** and **2 CPUs** to start. Set the request timeout to **900 seconds** to allow initial training; Cloud Run's default request timeout is 300 seconds. Adjust these after observing real build and request performance.
6. Under ingress/authentication, allow unauthenticated invocations if the website's visitors should call the API directly. If authentication is required, the frontend needs a secure server-side integration; do not put service account credentials in browser code.
7. Create the service and follow the build/deployment logs. Open the generated `run.app` URL plus `/health`; it should report `status: ok` and all six files as `true`. Open `/docs` to try the API.
8. Add `CORS_ORIGINS` in the service's variables, using the deployed frontend origin (for example `https://your-site.example`). For local frontend work, use `http://localhost:3000,http://localhost:5173`. CORS is not authentication; avoid leaving `*` in place for a public production API.
9. In the Bolt/Lovable frontend, use the Cloud Run service URL as the API base and POST JSON to `/api/recommendations`. After pushing backend changes to `main`, Cloud Build can automatically build and deploy a new revision when continuous deployment is enabled.

Google Cloud's repository deployment guide: https://cloud.google.com/run/docs/continuous-deployment

## Model behavior to review before launch

The supplied script uses synthetic market indicators and synthetic rate lags seeded with 42 for inference. Those behaviors are preserved, so recommendations are not driven by live market values. The original `quantity_kg = quantity` assignment and freight cost multiplication by vessel DWT are also unchanged; validate units and cost assumptions before presenting the output as an operational quote.
