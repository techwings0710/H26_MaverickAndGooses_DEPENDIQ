# Build manually after reviewing docs/verification.md. Never built by the API.
FROM python:3.12-slim
COPY wheelhouse/ /wheels/
RUN python -m pip install --no-index --only-binary=:all: --find-links=/wheels pytest
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
USER 65534:65534
WORKDIR /repo
