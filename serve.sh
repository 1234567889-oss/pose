#!/bin/sh
# Serve the app locally: ./serve.sh [port]   (open http://localhost:8080 ; PWA install needs HTTPS or localhost)
cd "$(dirname "$0")" && python3 -m http.server "${1:-8080}"
