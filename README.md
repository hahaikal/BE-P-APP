**model train**
python train_model.py

**berishkan redis**
docker-compose exec redis redis-cli FLUSHDB

**cek redis**
docker compose exec redis redis-cli
KEYS *
LLEN celery
ZCARD unacked

**mengambil data matches manual**
docker compose exec worker celery -A app.tasks call app.tasks.discover_new_matches

**mengambil data odds manual**
docker compose exec worker celery -A app.tasks call app.tasks.record_odds_snapshot --args='[id, "api_id"]'

**masuk psql**
docker exec -it p_app_postgres sh
psql -U p_app_user -d p_app_db

**jalankan script**
dockercompose exec worker python reschedule_odds.py