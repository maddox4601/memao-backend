#!/bin/bash
set -eo pipefail

export GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID"
export GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET"
DEPLOY_DIR="/root/memao-backend"
cd $DEPLOY_DIR || exit 1

# 拉取最新代码
git fetch --tags origin master
git reset --hard origin/master
git clean -fd

# 更新 .env.pro
sed -i '/GOOGLE_CLIENT_/d' .env.pro
echo "" >> .env.pro
echo "GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID" >> .env.pro
echo "GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET" >> .env.pro

# 重建 Docker
docker compose --env-file .env.pro down --timeout 30
docker compose --env-file .env.pro up -d --build

# 等待 MySQL 健康
DB_READY=false
for i in $(seq 1 120); do
  if docker compose ps mysql | grep -q 'healthy'; then DB_READY=true; break; fi
  sleep 2
done
if ! $DB_READY; then echo 'MySQL startup timed out'; docker compose logs mysql; exit 1; fi

# 数据库迁移
echo "⚙️ 数据库迁移..."
docker compose exec -it backend bash -c '
set -eo pipefail
for i in $(seq 1 30); do
  if flask db current &>/dev/null; then break; fi
  sleep 2
done
flask db upgrade
'

echo "💚 健康检查..."
for i in {1..10}; do
  docker compose exec -T backend curl -sf http://localhost:5000/health > /dev/null
  if [ $? -eq 0 ]; then
    echo "✅ Backend healthy!" >&2
    break
  else
    echo "⏳ Waiting for backend health... ($i/10)" >&2
    sleep 3
  fi
done

echo "🎉 Deployment successful!" >&2

echo "🧹 清理旧容器和资源..."
docker system prune -f --volumes --filter "until=24h" && \
  echo "✅ Docker cleanup completed!" || echo "⚠️ Docker prune failed"

