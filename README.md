**jalankan server**
uvicorn app.main:app --reload

**Jalankan Celery Worker**
celery -A worker.celery_app worker --loglevel=info

**Jalankan Celery Beat (Scheduler)**
celery -A worker.celery_app beat --loglevel=info

**model train**
python train_model.py

redis-cli ping