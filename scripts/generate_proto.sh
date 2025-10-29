#!/bin/bash

# Script para gerar código gRPC a partir do arquivo .proto
# Uso: ./scripts/generate_proto.sh

echo "🔨 Gerando código gRPC a partir do arquivo .proto..."

# Criar diretório para arquivos gerados se não existir
mkdir -p src/generated

# Gerar código Python a partir do .proto
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/generated \
    --grpc_python_out=./src/generated \
    ./proto/printing.proto

# Criar __init__.py no diretório generated
touch src/generated/__init__.py

echo "✅ Código gRPC gerado com sucesso em src/generated/"
echo "   - printing_pb2.py (mensagens)"
echo "   - printing_pb2_grpc.py (serviços)"
