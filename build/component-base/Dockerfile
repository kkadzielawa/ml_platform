FROM docker.io/library/python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/ml-platform/src

RUN groupadd --system --gid 10001 component \
    && useradd --system --uid 10001 --gid component --create-home --home-dir /home/component component \
    && mkdir -p /opt/ml-platform/src/ml_platform \
    && chown -R 10001:10001 /opt/ml-platform

COPY --chown=10001:10001 src/ml_platform/__init__.py /opt/ml-platform/src/ml_platform/__init__.py
COPY --chown=10001:10001 src/ml_platform/components /opt/ml-platform/src/ml_platform/components

WORKDIR /opt/ml-platform
USER 10001:10001
ENTRYPOINT ["python", "-m", "ml_platform.components.noop"]
