#!/bin/bash

# Script para iniciar o servidor de impressão
# Uso: ./scripts/run_server.sh [porta]

PORT=${1:-50051}

echo "🖨️  Iniciando Servidor de Impressão..."
echo "Porta: $PORT"
echo ""

cd "$(dirname "$0")/.."
python3 src/printer_server.py --port $PORT
