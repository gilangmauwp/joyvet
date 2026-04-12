.PHONY: help build start stop restart logs shell db-shell migrate makemigrations \
        seed test lint collectstatic createsuperuser setup

COMPOSE = docker-compose
EXEC    = $(COMPOSE) exec app

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build:          ## Build Docker images
	$(COMPOSE) build

start:          ## Start all services
	$(COMPOSE) up -d

stop:           ## Stop all services
	$(COMPOSE) down

restart:        ## Restart app only (fast)
	$(COMPOSE) restart app celery celery-beat

logs:           ## Tail app logs
	$(COMPOSE) logs -f app celery

shell:          ## Django shell
	$(EXEC) python manage.py shell

db-shell:       ## PostgreSQL shell
	$(COMPOSE) exec db psql -U joyvet -d joyvet

migrate:        ## Run migrations
	$(EXEC) python manage.py migrate

makemigrations: ## Create new migrations
	$(EXEC) python manage.py makemigrations

seed:           ## Load demo data (dev only)
	$(EXEC) python manage.py seed_demo_data

test:           ## Run pytest with coverage
	$(EXEC) pytest --cov=apps --cov-report=term-missing -v

lint:           ## Run flake8
	$(EXEC) flake8 apps/ joyvet/ api/ realtime/ frontend/

collectstatic:  ## Collect static files
	$(EXEC) python manage.py collectstatic --noinput

createsuperuser: ## Create Django admin superuser
	$(EXEC) python manage.py createsuperuser

# ── First-time setup ───────────────────────────────────────
setup:          ## Full first-time setup (build → start → migrate → seed)
	@echo "→ Building images..."
	$(COMPOSE) build
	@echo "→ Starting database and Redis..."
	$(COMPOSE) up -d db redis
	@sleep 8
	@echo "→ Starting all services..."
	$(COMPOSE) up -d
	@sleep 5
	@echo "→ Running migrations..."
	$(EXEC) python manage.py migrate
	@echo "→ Seeding demo data..."
	$(EXEC) python manage.py seed_demo_data
	@echo ""
	@echo "✓ JoyVet Care is running at https://localhost"
	@echo "  Admin: https://localhost/admin/"
	@echo "  Demo login: admin / joyvet2024"
