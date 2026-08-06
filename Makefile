SSL_CERT_FILE := $(shell .venv/bin/python -c "import certifi; print(certifi.where())")
export SSL_CERT_FILE

.PHONY: serve test pipeline

serve:
	.venv/bin/uvicorn src.main:app --port 8000

test:
	.venv/bin/python -m pytest tests/ -v

pipeline:
	.venv/bin/python run_pipeline.py
