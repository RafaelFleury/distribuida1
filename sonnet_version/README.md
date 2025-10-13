# Sistema de Impressão Distribuída

Sistema de impressão distribuída com exclusão mútua usando:

- **gRPC** para comunicação
- **Algoritmo de Ricart-Agrawala** para exclusão mútua distribuída
- **Relógios Lógicos de Lamport** para ordenação de eventos

## 🚀 Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Gerar código gRPC

```bash
chmod +x scripts/generate_proto.sh
./scripts/generate_proto.sh
```

Ou manualmente:

```bash
python3 -m grpc_tools.protoc -I./proto --python_out=./src/generated --grpc_python_out=./src/generated ./proto/printing.proto
```

## 📦 Estrutura do Projeto

```
sonnet_version/
├── proto/
│   └── printing.proto              # Definição dos serviços gRPC
├── src/
│   ├── generated/                  # Código gerado (não editar)
│   │   ├── printing_pb2.py
│   │   └── printing_pb2_grpc.py
│   ├── lamport_clock.py           # Implementação do relógio de Lamport
│   ├── printer_server.py          # Servidor de impressão "burro"
│   └── printing_client.py         # Cliente inteligente
├── scripts/
│   ├── generate_proto.sh          # Script para gerar código gRPC
│   ├── run_server.sh              # Script para iniciar servidor
│   └── run_client.sh              # Script para iniciar clientes
├── docs/
│   └── relatorio.md               # Relatório técnico
├── requirements.txt               # Dependências Python
└── README.md                      # Este arquivo
```

## 🎯 Como Executar

### Terminal 1 - Servidor de Impressão (Burro)

```bash
python3 src/printer_server.py --port 50051
```

### Terminal 2 - Cliente 1

```bash
python3 src/printing_client.py --id 1 --port 50052 --server localhost:50051 --clients localhost:50053,localhost:50054
```

### Terminal 3 - Cliente 2

```bash
python3 src/printing_client.py --id 2 --port 50053 --server localhost:50051 --clients localhost:50052,localhost:50054
```

### Terminal 4 - Cliente 3

```bash
python3 src/printing_client.py --id 3 --port 50054 --server localhost:50051 --clients localhost:50052,localhost:50053
```

## 🏗️ Arquitetura

### Servidor de Impressão "Burro" (Porta 50051)

- **NÃO** participa do algoritmo de exclusão mútua
- **NÃO** conhece outros clientes
- Apenas recebe requisições e imprime mensagens
- Implementa apenas `PrintingService`

### Clientes Inteligentes (Portas 50052+)

- **Implementam** `MutualExclusionService` (como servidores gRPC)
- **Usam** `PrintingService` do servidor burro (como clientes gRPC)
- **Usam** `MutualExclusionService` de outros clientes (como clientes gRPC)
- Coordenam exclusão mútua usando Ricart-Agrawala
- Mantêm relógios de Lamport sincronizados

## 📊 Algoritmo de Ricart-Agrawala

### Estados

- `RELEASED`: Não quer acessar o recurso
- `WANTED`: Quer acessar, aguardando permissões
- `HELD`: Está usando o recurso

### Fluxo

1. Cliente quer imprimir → Estado `WANTED`
2. Envia `RequestAccess` para todos os outros clientes
3. Aguarda `AccessResponse` de todos
4. Recebe todas as respostas → Estado `HELD`
5. Imprime no servidor burro
6. Estado `RELEASED` → Envia `ReleaseAccess` para todos

## 🕐 Relógios de Lamport

- Incrementado a cada evento local
- Atualizado ao receber mensagem: `max(local, received) + 1`
- Usado para ordenar requisições concorrentes
- Desempate por `client_id` (menor ID tem prioridade)

## 🧪 Testes

### Cenário 1: Sem Concorrência

- 1 cliente solicita impressão
- Obtém acesso imediatamente
- Imprime e libera

### Cenário 2: Concorrência

- Múltiplos clientes solicitam simultaneamente
- Ordenação por timestamp de Lamport
- Cliente com menor timestamp imprime primeiro

## 📝 Entregáveis

- [x] Código fonte completo
- [x] Scripts de execução
- [x] Manual de execução (README.md)
- [x] Relatório técnico (docs/relatorio.md)

## 🔧 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'grpcio'"

**Solução:** Instalar dependências

```bash
pip install -r requirements.txt
```

### Erro: "ModuleNotFoundError: No module named 'printing_pb2'"

**Causa:** Código gRPC não foi gerado  
**Solução:** Executar o script de geração

```bash
bash scripts/generate_proto.sh
```

### Erro: "Address already in use" ou "Failed to bind"

**Causa:** Porta já está ocupada por outro processo  
**Soluções:**

1. Verificar processos usando a porta:

```bash
lsof -i :50051  # Ou 50052, 50053, etc.
```

2. Matar processo específico:

```bash
kill <PID>
```

3. Usar porta diferente:

```bash
python3 src/printer_server.py --port 50061
python3 src/printing_client.py --id 1 --port 50062 --server localhost:50061 ...
```

### Cliente aguarda indefinidamente e não imprime

**Causas possíveis:**

1. **Servidor não está rodando**

   - Verificar se `printer_server.py` está ativo no Terminal 1
   - Conferir se porta do servidor está correta (`--server localhost:50051`)

2. **Outro cliente offline**

   - Cliente aguarda resposta de cliente que não existe
   - Solução: Remover cliente offline da lista `--clients`
   - Sistema remove automaticamente após timeout de 5s

3. **Lista de clientes incorreta**
   - Verificar se portas em `--clients` correspondem aos clientes realmente ativos
   - Exemplo para 2 clientes:

     ```bash
     # Cliente 1
     python3 src/printing_client.py --id 1 --port 50052 --server localhost:50051 --clients localhost:50053

     # Cliente 2
     python3 src/printing_client.py --id 2 --port 50053 --server localhost:50051 --clients localhost:50052
     ```

### Logs não aparecem ou são truncados

**Solução:** Usar output unbuffered

```bash
python3 -u src/printer_server.py --port 50051
python3 -u src/printing_client.py --id 1 --port 50052 ...
```

### Erro: "Permission denied" ao executar scripts

**Solução:** Dar permissão de execução

```bash
chmod +x scripts/*.sh
```

### Timestamps não estão sincronizados

**Isso é esperado!** Relógios de Lamport são **lógicos**, não físicos.  
O importante é a **ordenação** dos eventos, não o valor absoluto dos timestamps.

### Cliente imprime mas servidor não mostra nada

**Causa:** Servidor e cliente podem estar em versões diferentes do proto  
**Solução:**

1. Regenerar código gRPC: `bash scripts/generate_proto.sh`
2. Reiniciar servidor e clientes

### Como parar todos os processos de uma vez?

```bash
# Matar todos os processos Python com "printing" no nome
pkill -f "printing_client.py"
pkill -f "printer_server.py"
```

Ou em cada terminal: `Ctrl+C`

## 👥 Equipe

- Grupo: [PREENCHER]
- Membros: [PREENCHER]

## 📅 Prazo

**19/10/2025 às 23:59**

## 📚 Referências

- Ricart & Agrawala (1981) - "An optimal algorithm for mutual exclusion in computer networks"
- Lamport (1978) - "Time, clocks, and the ordering of events in a distributed system"
- Documentação gRPC: https://grpc.io/
