#!/bin/bash

# Script para iniciar um cliente
# Uso: ./scripts/run_client.sh <id> <porta> <servidor> <outros_clientes>
# Exemplo: ./scripts/run_client.sh 1 50052 localhost:50051 "localhost:50053,localhost:50054"

if [ $# -lt 3 ]; then
    echo "Uso: $0 <id> <porta> <servidor> [outros_clientes]"
    echo ""
    echo "Exemplo:"
    echo "  $0 1 50052 localhost:50051 \"localhost:50053,localhost:50054\""
    exit 1
fi

CLIENT_ID=$1
PORT=$2
SERVER=$3
CLIENTS=${4:-""}

echo "🖥️  Iniciando Cliente $CLIENT_ID..."
echo "Porta: $PORT"
echo "Servidor: $SERVER"
echo "Outros clientes: $CLIENTS"
echo ""

cd "$(dirname "$0")/.."
python3 src/printing_client.py --id $CLIENT_ID --port $PORT --server $SERVER --clients "$CLIENTS"
