# LinkedIn auto-apply bot: local Docker Compose app. `make up`, then open http://localhost:8080
COMPOSE := docker compose --env-file .env -f docker/compose.yaml
TEST_DB_URL := postgresql+psycopg://applier:$${POSTGRES_PASSWORD}@postgres:5432/applier_test

.DEFAULT_GOAL := help
.PHONY: help env up down logs test test-backend test-frontend seed migrate shell-api shell-worker shell-db backup restore

help: ## Show the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

env:
	@./docker/stack/init-env.sh

up: env ## Build and start everything (creates .env on first run)
	$(COMPOSE) up -d --build --wait
	@echo ""
	@echo "Applier is running: http://localhost:8080"

down: ## Stop everything (data is kept)
	$(COMPOSE) down

logs: ## Follow the logs of all services
	$(COMPOSE) logs -f --tail=200

test: test-backend test-frontend ## Run all tests (backend in the api container, frontend in node)

test-backend: env
	$(COMPOSE) build api
	$(COMPOSE) up -d --wait postgres
	$(COMPOSE) exec -T postgres sh -c 'psql -U applier -d applier -tAc "SELECT 1 FROM pg_database WHERE datname = '\''applier_test'\''" | grep -q 1 || createdb -U applier applier_test'
	$(COMPOSE) run --rm --no-deps api sh -c 'TEST_DATABASE_URL="$(TEST_DB_URL)" python -m pytest tests -q'

test-frontend:
	docker build -q --target test -f docker/stack/frontend.Dockerfile -t applier-frontend-test . >/dev/null
	docker run --rm applier-frontend-test

seed: env ## Import config/*.py, CSV history and resume; add missing secrets to .env
	$(COMPOSE) up -d --wait api
	$(COMPOSE) run --rm --no-deps -v "$(CURDIR):/legacy:ro" -v "$(CURDIR)/.env:/legacy-env/.env" api \
		python -m app.seed --source /legacy --env-file /legacy-env/.env --write-env
	$(COMPOSE) up -d --wait

migrate: env ## Apply database migrations
	$(COMPOSE) run --rm api alembic upgrade head

shell-api: ## Shell in the api container
	$(COMPOSE) exec api bash

shell-worker: ## Shell in the worker container
	$(COMPOSE) exec worker bash

shell-db: ## psql in the database
	$(COMPOSE) exec postgres psql -U applier applier

backup: ## Dump the database to backups/<timestamp>.sql
	@mkdir -p backups
	$(COMPOSE) exec -T postgres pg_dump -U applier --clean --if-exists applier > backups/$$(date +%Y%m%d-%H%M%S).sql
	@ls -t backups/*.sql | head -1

restore: ## Restore a dump: make restore FILE=backups/<file>.sql
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/<file>.sql" && exit 1)
	@test -f "$(FILE)" || (echo "No such file: $(FILE)" && exit 1)
	$(COMPOSE) stop worker api
	$(COMPOSE) exec -T postgres psql -U applier -d applier -v ON_ERROR_STOP=1 -q < "$(FILE)"
	$(COMPOSE) up -d --wait
