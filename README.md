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

Keep the column names and units expected by the original model. This GitHub repository is private because it contains the data. For larger or more sensitive datasets, store them separately and set `DATA_DIR` to the mounted or downloaded directory. Render's container filesystem is temporary by default, so a model cache written at runtime is not durable across instance replacement. Models train on the first recommendation request and the cache is reused only while an instance remains alive.

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

## Deploy to Render

This GitHub repository is rooted at the backend files; the `Dockerfile` is at the repository root.

1. In the Render Dashboard, choose **New > Web Service**, connect GitHub, and select the private repository `NorthStrake/kitty` on branch `main`.
2. Set **Root Directory** to blank (repository root) and **Runtime** to **Docker**. Keep the Dockerfile path as `./Dockerfile` and leave **Docker Command** blank so Render uses the command in the Dockerfile.
3. Choose a service name and region. Select a plan; the free service spins down after inactivity, so its next request can have a cold start.
4. In **Advanced**, set the health check path to `/health`. Leave `PORT` unset; Render provides it, and the Dockerfile binds Uvicorn to `0.0.0.0:$PORT` (default 10000).
5. Add `CORS_ORIGINS` as a comma-separated list of the frontend origins that will call this API. For local frontend work use `http://localhost:3000,http://localhost:5173`; add the deployed frontend URL when it exists. The code currently defaults to `*` if this variable is omitted.
6. Click **Create Web Service** and follow the build/deploy logs. When it is live, open the Render URL plus `/health`; it should say `status: ok` and show all six files as `true`. Visit `/docs` to try the endpoint.
7. In Bolt/Lovable frontend code, set the API base URL to the Render service URL and POST JSON to `/api/recommendations`. Figma is a design tool; its exported frontend still needs to be hosted somewhere. Render can automatically redeploy this API after pushes to the connected branch.

Render's [web service deployment guide](https://render.com/docs/web-services) and [Docker guide](https://render.com/docs/docker) describe these settings.

## Model behavior to review before launch

The supplied script uses synthetic market indicators and synthetic rate lags seeded with 42 for inference. Those behaviors are preserved, so recommendations are not driven by live market values. The original `quantity_kg = quantity` assignment and freight cost multiplication by vessel DWT are also unchanged; validate units and cost assumptions before presenting the output as an operational quote.
