#!/usr/bin/env bash
# SatTrack: deployment to Azure Container Apps (CLI variant of docs/DEPLOYMENT.md, steps 0-5).
# Authentication (step 6) is configured in the Azure Portal, see docs/DEPLOYMENT.md.
#
# Usage (from the repository root, Docker running, `az login` done):
#   bash scripts/deploy.sh            # first deployment, tag v1
#   TAG=v2 bash scripts/deploy.sh     # new version: rebuild, push and update the image only
#
# WARNING: this script creates paid Azure resources (Container Registry Basic ~5 USD/month).
set -euo pipefail

# ---- parameters ----
RG="${RG:-rg-sattrack}"
LOCATION="${LOCATION:-westeurope}"
ACR="${ACR:-acrsattrackCHANGEME}"   # globally unique, lowercase letters and digits only
ENV_NAME="${ENV_NAME:-cae-sattrack}"
APP="${APP:-ca-sattrack}"
TAG="${TAG:-v1}"
# --------------------

if [[ "$ACR" == *CHANGEME* ]]; then
  echo "Set a unique registry name first, e.g.: ACR=acrsattrack123 bash scripts/deploy.sh" >&2
  exit 1
fi

IMAGE="$ACR.azurecr.io/sattrack:$TAG"
step() { printf '\n==> %s\n' "$*"; }

step "Subscription"
az account show --query "{name:name, id:id}" -o table

if az containerapp show -n "$APP" -g "$RG" >/dev/null 2>&1; then
  step "Container app exists: building $IMAGE and updating"
  az acr login --name "$ACR"
  docker build --platform linux/amd64 -t "$IMAGE" .
  docker push "$IMAGE"
  az containerapp update -n "$APP" -g "$RG" --image "$IMAGE" -o none
else
  step "Resource providers"
  for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry; do
    az provider register --namespace "$ns" --wait
  done

  step "Resource group $RG ($LOCATION)"
  az group create -n "$RG" -l "$LOCATION" -o none

  step "Container Registry $ACR (Basic)"
  az acr create -n "$ACR" -g "$RG" --sku Basic -l "$LOCATION" -o none

  step "Image $IMAGE (local Docker build; ACR Tasks are paused on free-credit subscriptions)"
  az acr login --name "$ACR"
  docker build --platform linux/amd64 -t "$IMAGE" .
  docker push "$IMAGE"

  step "Container Apps environment $ENV_NAME (creates a Log Analytics workspace)"
  az containerapp env create -n "$ENV_NAME" -g "$RG" -l "$LOCATION" -o none

  step "Container app $APP (quickstart image first, then registry via system identity)"
  az containerapp create -n "$APP" -g "$RG" --environment "$ENV_NAME" \
    --image mcr.microsoft.com/k8se/quickstart:latest \
    --target-port 80 --ingress external \
    --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 2 -o none
  az containerapp registry set -n "$APP" -g "$RG" --server "$ACR.azurecr.io" --identity system -o none
  az containerapp update -n "$APP" -g "$RG" --image "$IMAGE" -o none
  az containerapp ingress update -n "$APP" -g "$RG" --target-port 8000 -o none
fi

FQDN=$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)
step "Done: https://$FQDN"
echo "Next: health probes and authentication in the portal (docs/DEPLOYMENT.md, steps 5 and 6)."
