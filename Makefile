.PHONY: help install seed seed-real dev api web test build demo clean

PY := $(CURDIR)/.venv/bin/python
PIP := $(CURDIR)/.venv/bin/pip

help:
	@echo "make install    安装后端与前端依赖"
	@echo "make seed       导入样例数据（秒级）"
	@echo "make seed-real  导入真实数据（需仓库根 models.parquet）"
	@echo "make api        启动后端 :8000（热重载）"
	@echo "make web        启动前端 :5173"
	@echo "make test       跑后端测试"
	@echo "make build      构建前端"
	@echo "make demo       前端构建 + 后端单进程托管"

install:
	python3.12 -m venv .venv || true
	$(PIP) install -q -r backend/requirements-dev.txt
	cd frontend && npm install

seed:
	cd backend && $(PY) -m scripts.seed

seed-real:
	cd backend && $(PY) -m scripts.seed --source hubstats --limit 20000

api:
	cd backend && $(PY) -m uvicorn app:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && $(PY) -m pytest tests -q

build:
	cd frontend && npm run build

demo: build
	cd backend && $(PY) -m uvicorn app:app --port 8000

clean:
	rm -rf backend/.pytest_cache frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
