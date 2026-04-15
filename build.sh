#!/usr/bin/env bash
# Render build script — installs deps and builds frontend
set -e

echo "=== Installing backend dependencies ==="
pip install -r backend/requirements.txt

echo "=== Installing frontend dependencies ==="
cd frontend
npm install

echo "=== Building frontend ==="
npm run build
cd ..

echo "=== Build complete ==="
ls -la frontend/dist/
