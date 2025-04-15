FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && poetry config virtualenvs.create false \
  && poetry install --no-root

COPY . .

CMD ["python", "internet_shop/manage.py", "runserver", "0.0.0.0:8000"]
