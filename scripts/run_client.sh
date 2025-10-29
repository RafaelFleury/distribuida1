#!/bin/bash

# Script para iniciar um cliente com configuração automática
# Uso: ./scripts/run_client.sh <id> [total_clientes] [porta_servidor]
# Exemplo: ./scripts/run_client.sh 1          # Cliente 1 de 3 (padrão)
# Exemplo: ./scripts/run_client.sh 2 4        # Cliente 2 de 4
# Exemplo: ./scripts/run_client.sh 1 3 50061  # Cliente 1 de 3, servidor customizado

if [ $# -lt 1 ]; then
    echo "Uso: $0 <id> [total_clientes] [porta_servidor]"
    echo ""
    echo "Argumentos:"
    echo "  id              - ID do cliente (obrigatório, ex: 1, 2, 3...)"
    echo "  total_clientes  - Número total de clientes (padrão: 3)"
    echo "  porta_servidor  - Porta do servidor (padrão: 50051)"
    echo ""
    echo "Exemplos:"
    echo "  $0 1                  # Cliente 1 de 3 (porta 50052)"
    echo "  $0 2                  # Cliente 2 de 3 (porta 50053)"
    echo "  $0 3                  # Cliente 3 de 3 (porta 50054)"
    echo "  $0 1 4                # Cliente 1 de 4 (porta 50052)"
    echo "  $0 2 4 50061          # Cliente 2 de 4, servidor na 50061"
    echo ""
    echo "Portas calculadas automaticamente:"
    echo "  Servidor: 50051 (ou valor customizado)"
    echo "  Cliente 1: 50052"
    echo "  Cliente 2: 50053"
    echo "  Cliente N: 50051 + N"
    exit 1
fi

CLIENT_ID=$1
TOTAL_CLIENTS=${2:-3}
SERVER_PORT=${3:-50051}

# Calcula a porta do cliente: 50051 + CLIENT_ID
PORT=$((50051 + CLIENT_ID))
SERVER="localhost:$SERVER_PORT"

# Gera lista de outros clientes automaticamente
CLIENTS=""
for i in $(seq 1 $TOTAL_CLIENTS); do
    if [ $i -ne $CLIENT_ID ]; then
        CLIENT_PORT=$((50051 + i))
        if [ -z "$CLIENTS" ]; then
            CLIENTS="localhost:$CLIENT_PORT"
        else
            CLIENTS="$CLIENTS,localhost:$CLIENT_PORT"
        fi
    fi
done

echo "🖥️  Iniciando Cliente $CLIENT_ID de $TOTAL_CLIENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 Porta do cliente: $PORT"
echo "🖨️  Servidor: $SERVER"
echo "👥 Outros clientes: $CLIENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$(dirname "$0")/.."
python3 src/printing_client.py --id $CLIENT_ID --port $PORT --server $SERVER --clients "$CLIENTS"
