FROM python:3.10 as requirements-stage

WORKDIR /app

ARG POETRY_VERSION=1.2.0a2
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

COPY pyproject.toml poetry.lock /app/
RUN pip install "poetry==$POETRY_VERSION" && \
    poetry export --without-hashes --no-interaction --no-ansi -f requirements.txt -o requirements.txt && \
    pip install --prefix=/runtime --force-reinstall -r requirements.txt

FROM python:3.10-slim

WORKDIR /app

COPY --from=requirements-stage /runtime /usr/local
COPY . ./

RUN chmod +x scripts/start.sh
EXPOSE 80

ENV ASGI_ROOT_PATH=/
CMD ["/app/scripts/start.sh"]