# Deploying Nucleus MCP to Cloud Run

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth login`)
- Docker installed locally (for manual builds)

## One-time setup

```bash
export PROJECT_ID=your-gcp-project
export REGION=asia-south1   # Mumbai — change to your preferred region
export SERVICE=nucleus-mcp

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Create Artifact Registry repo
gcloud artifacts repositories create nucleus \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID

# Grant Cloud Build SA permissions
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/artifactregistry.writer"
```

## Deploy (single command)

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions \
    _PROJECT_ID=$PROJECT_ID,\
    _REGION=$REGION,\
    _SERVICE=$SERVICE,\
    _TENANT_ID=myorg \
  --project=$PROJECT_ID
```

Cloud Build will:
1. Build the Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run (`CMD=http` mode)
4. Hit `/health` and confirm it's up

## Deployment modes

### Solo (single tenant, no auth)
```bash
--substitutions _TENANT_ID=myorg
# All requests routed to one brain
```

### Multi-tenant (SaaS)
```bash
# Set these as Cloud Run env vars after deploy:
gcloud run services update nucleus-mcp \
  --region=$REGION \
  --set-env-vars="NUCLEUS_TENANT_MAP={\"tok_abc\":\"acme\",\"tok_xyz\":\"globex\"},NUCLEUS_REQUIRE_AUTH=true,NUCLEUS_BRAIN_ROOT=/app/tenants"
```

For multi-tenant, mount a persistent volume or use Cloud Firestore for brain storage (Nucleus supports `google-cloud-firestore` natively).

## Verify manually

```bash
URL=$(gcloud run services describe $SERVICE \
  --region=$REGION --format='value(status.url)')

# Identity card
curl $URL/

# Health
curl $URL/health

# MCP initialize
curl -X POST $URL/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Point an MCP client at it

```json
{
  "mcpServers": {
    "nucleus-cloud": {
      "url": "https://your-cloud-run-url.run.app/mcp",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

## Local Docker test before deploying

```bash
docker build -t nucleus-mcp .

# Solo mode
docker run -p 8080:8080 \
  -e NUCLEUS_TENANT_ID=test \
  -e NUCLEAR_BRAIN_PATH=/app/.brain \
  -v $(pwd)/.brain:/app/.brain \
  nucleus-mcp http

# Verify
curl http://localhost:8080/health
```
