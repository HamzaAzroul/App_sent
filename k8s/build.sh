#!/bin/bash

set -euo pipefail

### 🔧 Variables
APP_NAME="sentiment-app"
DOCKER_USERNAME="hamzaazroul"
IMAGE_TAG="latest"
APP_DIR="./APP_SENT2"
GRAFANA_PORT=3000
PROM_PORT=9090
APP_PORT=8000
NETWORK_NAME="sentiment-net"

### 🎨 Couleurs
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
RESET="\033[0m"

log() { echo -e "${BLUE}➡ $1${RESET}"; }
success() { echo -e "${GREEN}✔ $1${RESET}"; }
warn() { echo -e "${YELLOW}⚠ $1${RESET}"; }

### 🧼 Étape 1 : Nettoyage
log "Nettoyage des anciens conteneurs..."
docker rm -f $APP_NAME grafana prometheus postgres || true
docker network rm $NETWORK_NAME || true
success "Anciennes instances supprimées"

### 🌐 Étape 2 : Création réseau
log "Création d’un réseau Docker isolé : $NETWORK_NAME"
docker network create $NETWORK_NAME
success "Réseau Docker $NETWORK_NAME prêt"

### 🛠️ Étape 3 : Build de l’image app
log "Build de l’image $APP_NAME depuis $APP_DIR..."
docker build -t $DOCKER_USERNAME/$APP_NAME:$IMAGE_TAG "$APP_DIR"
success "Image construite : $DOCKER_USERNAME/$APP_NAME:$IMAGE_TAG"

### 🐘 Étape 4 : Lancement PostgreSQL
log "Lancement de PostgreSQL..."
docker run -d \
  --name postgres \
  --network $NETWORK_NAME \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin \
  -e POSTGRES_DB=sentiment_db \
  postgres:15
success "PostgreSQL prêt sur le réseau $NETWORK_NAME"

### 🚀 Étape 5 : Lancement de l'application
log "Lancement de l'application $APP_NAME..."
docker run -d \
  --name $APP_NAME \
  --network $NETWORK_NAME \
  -p $APP_PORT:$APP_PORT \
  -e DB_HOST=postgres \
  -e DB_USER=admin \
  -e DB_PASSWORD=admin \
  -e DB_NAME=sentiment_db \
  $DOCKER_USERNAME/$APP_NAME:$IMAGE_TAG
success "$APP_NAME accessible sur http://localhost:$APP_PORT"

### 📊 Étape 6 : Lancement Prometheus
log "Lancement de Prometheus..."
docker run -d \
  --name prometheus \
  --network $NETWORK_NAME \
  -p $PROM_PORT:9090 \
  -v "$(pwd)/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml" \
  prom/prometheus
success "Prometheus accessible sur http://localhost:$PROM_PORT"

### 📈 Étape 7 : Lancement Grafana
log "Lancement de Grafana..."
docker run -d \
  --name grafana \
  --network $NETWORK_NAME \
  -p $GRAFANA_PORT:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana
success "Grafana accessible sur http://localhost:$GRAFANA_PORT"

### ✅ Résumé final
success "Déploiement local terminé ✅"
echo ""
echo -e "${GREEN}🌍 Application : http://localhost:$APP_PORT${RESET}"
echo -e "${GREEN}📊 Grafana : http://localhost:$GRAFANA_PORT (admin/admin)${RESET}"
echo -e "${GREEN}📈 Prometheus : http://localhost:$PROM_PORT${RESET}"
echo -e "${GREEN}🐘 PostgreSQL : internal container on $NETWORK_NAME${RESET}"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
