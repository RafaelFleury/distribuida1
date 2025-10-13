# 📋 Plano de Ação - Sistema de Impressão Distribuída

**Prazo:** 19/10/2025 (faltam 6 dias!)  
**Status:** 🚀 Planejamento

---

## 🎯 Visão Geral do Projeto

Implementar um sistema distribuído com:

- **Servidor de impressão "burro"** (porta 50051) - apenas recebe e imprime
- **Clientes inteligentes** (portas 50052+) - coordenam exclusão mútua entre si
- **Algoritmo de Ricart-Agrawala** para exclusão mútua distribuída
- **Relógios Lógicos de Lamport** para ordenação de eventos
- **gRPC** para comunicação entre processos

---

## 📅 Cronograma Sugerido (6 dias)

### **Dia 1 (13/10)** - Preparação e Ambiente

- [ ] Escolher linguagem de programação (Python recomendado)
- [ ] Configurar ambiente de desenvolvimento
- [ ] Instalar dependências do gRPC
- [ ] Criar estrutura de pastas do projeto

### **Dia 2 (14/10)** - Definição do Protocolo

- [ ] Criar arquivo `.proto` com definições de mensagens
- [ ] Gerar código gRPC a partir do `.proto`
- [ ] Validar compilação sem erros

### **Dia 3 (15/10)** - Servidor de Impressão

- [ ] Implementar servidor "burro" básico
- [ ] Adicionar simulação de delay (2-3s)
- [ ] Testar servidor isoladamente

### **Dia 4 (16/10)** - Cliente Base

- [ ] Implementar classe do relógio de Lamport
- [ ] Criar estrutura básica do cliente
- [ ] Implementar comunicação com servidor de impressão
- [ ] Testar 1 cliente enviando mensagens ao servidor

### **Dia 5 (17/10)** - Algoritmo de Ricart-Agrawala

- [ ] Implementar lógica de requisição de acesso
- [ ] Implementar lógica de resposta a requisições
- [ ] Implementar fila de requisições pendentes
- [ ] Implementar liberação de recurso
- [ ] Testar com 2-3 clientes simultâneos

### **Dia 6 (18/10)** - Testes e Documentação

- [ ] Executar cenários de teste obrigatórios
- [ ] Corrigir bugs encontrados
- [ ] Criar scripts de execução
- [ ] Escrever relatório técnico
- [ ] Gravar vídeo de demonstração (opcional)

### **Dia 7 (19/10)** - Finalização e Entrega

- [ ] Revisão final do código
- [ ] Verificar todos os entregáveis
- [ ] Enviar trabalho antes das 23:59

---

## 🏗️ Estrutura de Arquivos Sugerida

```
sonnet_version/
├── proto/
│   └── printing.proto              # Definição dos serviços gRPC
├── generated/                      # Código gerado pelo protoc
│   ├── printing_pb2.py
│   └── printing_pb2_grpc.py
├── src/
│   ├── lamport_clock.py           # Implementação do relógio de Lamport
│   ├── printer_server.py          # Servidor de impressão "burro"
│   ├── printing_client.py         # Cliente inteligente
│   └── ricart_agrawala.py         # Lógica do algoritmo
├── scripts/
│   ├── generate_proto.sh          # Script para gerar código gRPC
│   ├── run_server.sh              # Script para iniciar servidor
│   └── run_client.sh              # Script para iniciar clientes
├── tests/
│   └── test_scenarios.py          # Testes automatizados
├── docs/
│   └── relatorio.md               # Relatório técnico
├── requirements.txt               # Dependências Python
├── README.md                      # Manual de execução
└── .gitignore
```

---

## 🔧 Componentes Principais

### 1. **Relógio de Lamport** (`lamport_clock.py`)

```python
class LamportClock:
    def __init__(self):
        self.time = 0

    def increment(self):
        """Incrementa o relógio local"""
        self.time += 1
        return self.time

    def update(self, received_time):
        """Atualiza com max(local, received) + 1"""
        self.time = max(self.time, received_time) + 1
        return self.time

    def get_time(self):
        """Retorna tempo atual"""
        return self.time
```

### 2. **Servidor de Impressão Burro** (`printer_server.py`)

**Responsabilidades:**

- ✅ Implementar apenas `PrintingService`
- ✅ Receber mensagens via `SendToPrinter`
- ✅ Imprimir com formato: `[TS: {timestamp}] CLIENTE {id}: {mensagem}`
- ✅ Delay de 2-3 segundos
- ✅ Retornar confirmação
- ❌ **NÃO** implementa `MutualExclusionService`
- ❌ **NÃO** conhece outros clientes

### 3. **Cliente Inteligente** (`printing_client.py`)

**Papéis Duplos:**

- **Como Servidor gRPC:** Implementa `MutualExclusionService` para receber requisições de outros clientes
- **Como Cliente gRPC:** Usa `PrintingService` do servidor burro e `MutualExclusionService` de outros clientes

**Estado Interno:**

```python
class PrintingClient:
    def __init__(self, client_id, port, server_address, other_clients):
        self.client_id = client_id
        self.port = port
        self.lamport_clock = LamportClock()
        self.request_number = 0

        # Para Ricart-Agrawala
        self.state = "RELEASED"  # RELEASED, WANTED, HELD
        self.pending_replies = set()
        self.deferred_replies = []
        self.current_request_timestamp = None

        # Conexões
        self.printer_stub = None  # Para servidor burro
        self.client_stubs = {}    # Para outros clientes
```

### 4. **Algoritmo de Ricart-Agrawala** (`ricart_agrawala.py`)

**Estados:**

- `RELEASED`: Não quer acessar recurso
- `WANTED`: Quer acessar, aguardando permissões
- `HELD`: Está usando o recurso

**Fluxo Principal:**

```
1. Cliente quer imprimir:
   - Estado → WANTED
   - Incrementa relógio de Lamport
   - Envia REQUEST para todos os outros clientes
   - Aguarda OK de todos

2. Cliente recebe REQUEST de outro:
   - Atualiza relógio de Lamport
   - SE estado == RELEASED:
       → Envia OK imediatamente
   - SE estado == WANTED:
       → Compara timestamps (Lamport, client_id)
       → Se meu timestamp é menor: adia resposta
       → Se meu timestamp é maior: envia OK
   - SE estado == HELD:
       → Adia resposta para depois

3. Cliente recebe todos os OKs:
   - Estado → HELD
   - Envia mensagem para servidor burro
   - Aguarda confirmação de impressão
   - Estado → RELEASED
   - Envia OK para todos os pedidos adiados
   - Limpa fila de adiados
```

---

## 🔍 Casos de Teste Obrigatórios

### **Cenário 1: Funcionamento Básico**

```bash
# Terminal 1: Servidor
python3 printer_server.py --port 50051

# Terminal 2: Cliente único
python3 printing_client.py --id 1 --port 50052 --server localhost:50051 --clients ""
```

**Resultado Esperado:**

- Cliente 1 solicita acesso
- Como não há concorrência, obtém acesso imediatamente
- Imprime mensagem no servidor burro
- Libera acesso

### **Cenário 2: Concorrência Simples**

```bash
# Terminal 1: Servidor
python3 printer_server.py --port 50051

# Terminal 2: Cliente 1
python3 printing_client.py --id 1 --port 50052 --server localhost:50051 --clients localhost:50053

# Terminal 3: Cliente 2
python3 printing_client.py --id 2 --port 50053 --server localhost:50051 --clients localhost:50052
```

**Resultado Esperado:**

- Clientes 1 e 2 solicitam acesso simultaneamente
- Ricart-Agrawala decide ordem baseado em timestamps
- Cliente com menor timestamp imprime primeiro
- Segundo cliente aguarda e imprime depois

### **Cenário 3: Concorrência com 3+ Clientes**

```bash
# Adicionar Terminal 4: Cliente 3
python3 printing_client.py --id 3 --port 50054 --server localhost:50051 --clients localhost:50052,localhost:50053
```

**Resultado Esperado:**

- Múltiplas requisições simultâneas
- Ordenação correta baseada em Lamport
- Sem deadlock ou starvation
- Exclusão mútua garantida

---

## 📦 Dependências (Python)

Criar `requirements.txt`:

```
grpcio==1.60.0
grpcio-tools==1.60.0
protobuf==4.25.1
```

Instalar:

```bash
pip install -r requirements.txt
```

---

## 📝 Checklist de Entregáveis

### Código Fonte

- [ ] `printing.proto` - Definição completa dos serviços
- [ ] `printer_server.py` - Servidor de impressão burro
- [ ] `printing_client.py` - Cliente inteligente
- [ ] `lamport_clock.py` - Implementação do relógio
- [ ] Código bem comentado e legível
- [ ] Tratamento de erros adequado

### Scripts de Execução

- [ ] Script para gerar código gRPC
- [ ] Script para iniciar servidor
- [ ] Script para iniciar clientes
- [ ] Instruções de uso claras

### Documentação

- [ ] `README.md` com manual de execução
- [ ] Comandos exatos para cada terminal
- [ ] Exemplos de uso
- [ ] Troubleshooting comum

### Relatório Técnico

- [ ] Explicação da arquitetura
- [ ] Diagramas de comunicação
- [ ] Análise do Ricart-Agrawala implementado
- [ ] Explicação dos relógios de Lamport
- [ ] Resultados dos testes (prints/logs)
- [ ] Dificuldades encontradas
- [ ] Soluções adotadas
- [ ] Conclusões

---

## 🎓 Critérios de Avaliação (10 pontos)

| Critério                                 | Peso     | Pontos   | Status |
| ---------------------------------------- | -------- | -------- | ------ |
| Corretude do algoritmo (Ricart-Agrawala) | 30%      | 3.0      | ⏳     |
| Sincronização de relógios (Lamport)      | 20%      | 2.0      | ⏳     |
| Comunicação cliente-servidor             | 10%      | 1.0      | ⏳     |
| Comunicação cliente-cliente              | 10%      | 1.0      | ⏳     |
| Funcionamento em múltiplos terminais     | 10%      | 1.0      | ⏳     |
| Código fonte e documentação              | 20%      | 2.0      | ⏳     |
| **TOTAL**                                | **100%** | **10.0** | ⏳     |

---

## 🚨 Pontos de Atenção

### ⚠️ CRÍTICO

1. **Servidor é "burro"**: NÃO implementa exclusão mútua
2. **Clientes são híbridos**: Atuam como servidor E cliente gRPC
3. **Ordenação por timestamp**: Usar (timestamp_lamport, client_id) para desempate
4. **Requests adiados**: Clientes devem manter fila de respostas adiadas
5. **Atualização de relógio**: Sempre atualizar ao receber/enviar mensagem

### ✅ Boas Práticas

- Usar logging para debug (não print)
- Adicionar timestamps em todas as mensagens
- Validar conexões antes de enviar
- Tratar exceções de rede
- Usar threading para servidor gRPC do cliente
- Adicionar graceful shutdown

### 🐛 Problemas Comuns

- **Deadlock**: Verificar lógica de comparação de timestamps
- **Starvation**: Garantir que todos recebem respostas
- **Race condition**: Proteger estado compartilhado com locks
- **Porta ocupada**: Verificar se portas estão disponíveis

---

## 📚 Referências Importantes

### Algoritmo de Ricart-Agrawala

- Ricart & Agrawala (1981) - Paper original
- Requer N-1 permissões para N processos
- Usa timestamps para ordenação
- Desempate: menor ID ganha

### Relógios de Lamport

- Lamport (1978) - "Time, Clocks, and the Ordering of Events"
- Relação happened-before (→)
- Incremento em eventos locais
- Atualização: max(local, received) + 1

### gRPC

- Documentação: https://grpc.io/
- Python quickstart: https://grpc.io/docs/languages/python/quickstart/
- Protobuf guide: https://protobuf.dev/

---

## 🎯 Próximos Passos Imediatos

1. **AGORA**: Definir equipe e linguagem de programação
2. **HOJE**: Configurar ambiente e instalar dependências
3. **AMANHÃ**: Criar arquivo `.proto` e testar geração de código
4. **DIA 15**: Implementar servidor burro e testar
5. **DIA 16-17**: Implementar clientes e Ricart-Agrawala
6. **DIA 18**: Testes completos e documentação
7. **DIA 19**: Revisão final e entrega

---

## 💡 Dicas Extras

### Para Debugging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [Cliente %(client_id)s] [TS: %(timestamp)s] %(message)s'
)
```

### Para Visualização

- Adicionar display em tempo real do estado do cliente
- Mostrar requisições pendentes
- Mostrar valor do relógio de Lamport
- Mostrar estado atual (RELEASED/WANTED/HELD)

### Para Relatório

- Capturar screenshots dos terminais
- Incluir logs de execução
- Criar diagramas de sequência
- Mostrar exemplo de ordenação por Lamport

---

**Boa sorte! 🚀**

_Última atualização: 13/10/2025_
