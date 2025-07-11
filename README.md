**model train**
python train_model.py

**run redis**
docker run -d --name redis-p-app -p 6379:6379 redis

**testing redis**
docker exec redis-p-app redis-cli ping

**jalankan Celery worker**
celery -A app.tasks.celery_app worker --loglevel=info 
celery -A app.tasks.celery_app beat --loglevel=info

**mengambil data matches manual**
docker compose exec worker celery -A app.tasks call app.tasks.discover_new_matches

**mengambil data odds manual**
docker compose exec worker celery -A app.tasks call app.tasks.record_odds_snapshot --args='[id, "api_id"]'