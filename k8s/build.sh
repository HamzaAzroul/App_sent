#!/bin/bash
set -e

echo "🧼 Nettoyage Docker : conteneurs, images, volumes, réseaux..."

# Arrêt des conteneurs en cours
if [ -n "$(docker ps -q)" ]; then
  echo "🛑 Arrêt des conteneurs..."
  docker stop $(docker ps -q)
else
  echo "✔️ Aucun conteneur en cours."
fi

# Suppression des conteneurs arrêtés
if [ -n "$(docker ps -a -q)" ]; then
  echo "🗑️ Suppression des conteneurs arrêtés..."
  docker rm $(docker ps -a -q)
fi

# Suppression ciblée des images liées à l’app
echo "🖼️ Suppression des images Docker personnalisées..."
docker images "hamzaazroul/*" -q | xargs -r docker rmi -f

# Nettoyage volumes, réseaux et cache
docker container prune -f
docker image prune -a -f
docker volume prune -f
docker network prune -f
docker system prune -f

echo "🔨 Construction des images Docker..."
docker compose build

echo "📤 Pousser les images sur Docker Hub..."

IMAGES=(
  "hamzaazroul/sentiment-app:latest"
)

# for img in "${IMAGES[@]}"; do
#   echo "📦 Push $img..."
#   docker push "$img"
# done

# ❌ COMMENTÉ : Docker Compose n'est pas utile ici, car Minikube/K8s va tout déployer
# echo "🚀 Lancement des conteneurs en local..."
# docker compose up -d

echo "♻️ Redémarrage du cluster Minikube..."
minikube delete || echo "✅ Aucun cluster Minikube existant."

minikube start --driver=docker --addons=metrics-server --v=4 --alsologtostderr

# ✅ Changement de contexte Docker vers Minikube (utile si tu build dans Minikube)
eval $(minikube docker-env)

echo "⏳ Attente de Minikube..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

echo "📁 Création des namespaces..."
kubectl create namespace sentiment-app || echo "✅ Namespace 'sentiment-app' existe déjà"
kubectl create namespace monitoring || echo "✅ Namespace 'monitoring' existe déjà"

echo "📦 Déploiement des manifests Kubernetes..."
kubectl apply -f .

echo "📥 Ajout des dépôts Helm..."
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

echo "📈 Installation de Grafana via Helm..."
helm install grafana grafana/grafana \
  --namespace monitoring --create-namespace \
  --set adminPassword='admin' \
  --set service.type=NodePort \
  --set persistence.enabled=false \
  --set datasources."datasources\.yaml".apiVersion=1 \
  --set datasources."datasources\.yaml".datasources[0].name=Prometheus \
  --set datasources."datasources\.yaml".datasources[0].type=prometheus \
  --set datasources."datasources\.yaml".datasources[0].url=http://prometheus-server.monitoring.svc.cluster.local \
  --set datasources."datasources\.yaml".datasources[0].access=proxy \
  --set datasources."datasources\.yaml".datasources[0].isDefault=true

echo "📊 Installation de Prometheus via Helm..."
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace

#minikube service grafana -n monitoring

echo "⏳ Attente que Grafana soit prêt..."
kubectl wait --namespace monitoring \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=grafana \
  --timeout=180s || echo "⚠️ Grafana non prêt (vérifie avec kubectl get pods -n monitoring)"

echo "🌐 Ouverture du dashboard Minikube..."
minikube dashboard &

echo "✅ Tout est prêt ! Application déployée, monitoring en place, et cluster fonctionnel."
