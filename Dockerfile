DOCKERFILE = """
# Мультистейдж сборка для оптимизации размера
FROM python:3.12-slim as base

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install poetry

# Настройки Poetry
ENV POETRY_NO_INTERACTION=1 \\
    POETRY_VENV_IN_PROJECT=1 \\
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.12-slim as production

# Создаем пользователя приложения
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Копируем виртуальное окружение
COPY --from=base /app/.venv /app/.venv

# Убеждаемся что используем виртуальное окружение
ENV PATH="/app/.venv/bin:$PATH"

# Копируем код приложения
COPY --chown=appuser:appuser . .

# Создаем необходимые директории
RUN mkdir -p logs uploads && chown -R appuser:appuser logs uploads

# Переключаемся на пользователя приложения
USER appuser

# Указываем порт приложения
EXPOSE 8000

# Команда запуска
CMD ["python", "-m", "app.main"]
