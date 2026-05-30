# ARTour Recommender API

FastAPI microservice for ARTour recommendations with two explicit endpoints:

- `POST /recommend/user-to-item`
- `GET /recommend/item-to-item/{id}`

The service uses a pragmatic Service-Repo-Handler structure:

- `app/api/routers/` for handlers
- `app/api/schemas/` for Pydantic contracts
- `app/services/` for Apriori, CBF, MCRS, and NLP memoization
- `app/repositories/` for JSON data loading from the ARTour backend
- `app/configs/` for static config and environment binding

## Data Flow

The repository fetches JSON from the ARTour backend endpoints:

- `/places`
- `/user-interactions`

The payload is converted directly into in-memory pandas DataFrames. No CSV file is read or written by the API.

## Startup Behavior

On startup, the app attempts an automatic refresh. If the backend is unavailable, the service stays up but returns a non-ready health state until `/refresh` succeeds.

## Run

```bash
uvicorn app.main:app --reload
```

## Environment Variables

- `ARTOUR_BACKEND_BASE_URL`
- `ARTOUR_PLACES_PATH`
- `ARTOUR_USER_INTERACTIONS_PATH`
- `ARTOUR_REQUEST_TIMEOUT_SECONDS`
- `ARTOUR_APRIORI_ABSOLUTE_SUPPORT`
- `ARTOUR_APRIORI_MAX_LEN`
- `ARTOUR_DEFAULT_K`
- `ARTOUR_DEFAULT_N`
- `ARTOUR_WEIGHT_COST`
- `ARTOUR_WEIGHT_BENEFIT`

## Example Requests

### User-to-item

```bash
curl -X POST http://localhost:8000/recommend/user-to-item \
  -H 'Content-Type: application/json' \
  -d '{"basket_ids":["p1","p2","p3"],"k":5}'
```

### Item-to-item

```bash
curl http://localhost:8000/recommend/item-to-item/p1?k=5
```

## Notes

- User-to-item pads missing Apriori results with CBF using the centroid of the full basket.
- Item-to-item pads missing Apriori results with CBF using the single anchor item.
- Sastrawi preprocessing is memoized at refresh time for faster text normalization.
- Apriori support is fixed at absolute 3 and converted to relative support on each refresh.
- MCRS rating normalization uses the fixed scale of 1.0 to 5.0.
