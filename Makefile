.PHONY: help up down restart logs build migrate superuser shell test seed clean

help:
	@echo "Rai Backend - Management Commands:"
	@echo "  make up          - Start all containers in background"
	@echo "  make down        - Stop all containers"
	@echo "  make build       - Rebuild and start containers"
	@echo "  make logs        - Tail logs from web container"
	@echo "  make migrate     - Run database migrations"
	@echo "  make seed        - Seed development test data"
	@echo "  make superuser   - Create Django admin superuser"
	@echo "  make shell       - Open Django shell in web container"
	@echo "  make test        - Run test suite"
	@echo "  make clean       - Remove pycache and temporary files"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up --build -d

restart:
	docker compose restart

logs:
	docker compose logs -f web

migrate:
	docker compose exec web python manage.py migrate

seed:
	docker compose exec web python manage.py seed_dev

superuser:
	docker compose exec web python manage.py createsuperuser

shell:
	docker compose exec web python manage.py shell

test:
	docker compose exec web python manage.py test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
