FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY apps ./apps
COPY core ./core
COPY adapters ./adapters
COPY infrastructure ./infrastructure
COPY configs ./configs
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home scanner
USER scanner
EXPOSE 8080
CMD ["python", "-m", "apps.scanner.main"]
