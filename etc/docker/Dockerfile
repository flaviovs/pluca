ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --yes --no-install-recommends \
           git \
           mariadb-client \
           postgresql-client \
    && python -m pip install --upgrade pip \
    && pip install py-postgresql mysql-connector-python \
    && useradd --create-home test \
    && install --directory --owner=test --group=test \
       /home/test/.cache /home/test/.cache/pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER test
