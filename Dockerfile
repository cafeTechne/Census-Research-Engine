FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt pytest

COPY . .
RUN pip install --no-cache-dir --no-deps -e .

# Offline self-check (never requires CENSUS_API_KEY or network)
CMD ["python", "-m", "census", "doctor", "--verbose", "--json"]
