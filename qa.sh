set -e

ROOT=$(git rev-parse --show-toplevel)

docker run --rm -v "$ROOT:/app" -w /app python:3.7-slim \
       python -m doctest README.md

docker run --rm -v "$ROOT:/app" -w /app python:3.7-slim \
       python -m unittest
