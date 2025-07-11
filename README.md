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
docker compose exec celery_worker celery -A app.main.celery call app.tasks.fetch_and_process_matches