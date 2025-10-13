"""
Cliente Inteligente com Algoritmo de Ricart-Agrawala

Características:
- Implementa MutualExclusionService (como servidor gRPC)
- Usa PrintingService do servidor burro (como cliente gRPC)
- Usa MutualExclusionService de outros clientes (como cliente gRPC)
- Coordena exclusão mútua usando Ricart-Agrawala
- Mantém relógio de Lamport sincronizado
- Gera requisições de impressão automaticamente

Portas: 50052, 50053, 50054, ...
"""

import sys
import time
import random
import argparse
import logging
import threading
from concurrent import futures
from enum import Enum
import os

import grpc

# Ajustar path para imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.join(script_dir, 'generated'))

from lamport_clock import LamportClock, compare_timestamps
import printing_pb2
import printing_pb2_grpc


# Configurar logging
def setup_logger(client_id):
    """Configura logger específico para o cliente."""
    logger = logging.getLogger(f'Client-{client_id}')
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        f'[%(asctime)s] [CLIENTE {client_id}] [TS: %(timestamp)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


class ClientState(Enum):
    """Estados do cliente no algoritmo de Ricart-Agrawala."""
    RELEASED = "RELEASED"  # Não quer acessar o recurso
    WANTED = "WANTED"      # Quer acessar, aguardando permissões
    HELD = "HELD"          # Está usando o recurso


class PrintingClient(printing_pb2_grpc.MutualExclusionServiceServicer):
    """
    Cliente inteligente que implementa o algoritmo de Ricart-Agrawala
    para exclusão mútua distribuída.
    """
    
    def __init__(self, client_id, port, server_address, other_clients):
        """
        Inicializa o cliente.
        
        Args:
            client_id (int): ID único do cliente
            port (int): Porta para escutar conexões de outros clientes
            server_address (str): Endereço do servidor de impressão burro
            other_clients (list): Lista de endereços de outros clientes
        """
        self.client_id = client_id
        self.port = port
        self.server_address = server_address
        self.other_clients = other_clients
        
        # Relógio de Lamport
        self.clock = LamportClock()
        
        # Estado do algoritmo de Ricart-Agrawala
        self.state = ClientState.RELEASED
        self.request_number = 0
        self.current_request_timestamp = None
        self.pending_replies = set()  # IDs dos clientes que ainda não responderam
        self.deferred_replies = []    # Requisições que foram adiadas
        
        # Locks para sincronização
        self.state_lock = threading.Lock()
        self.replies_lock = threading.Lock()
        self.deferred_lock = threading.Lock()
        
        # Evento para sinalizar quando todas as respostas foram recebidas
        self.all_replies_received = threading.Event()
        
        # Conexões gRPC
        self.printer_stub = None
        self.client_stubs = {}
        
        # Logger específico do cliente
        self.logger = setup_logger(client_id)
        
        # Thread do servidor gRPC
        self.grpc_server = None
        self.grpc_thread = None
        
        # Flag para controlar execução
        self.running = True
    
    def log(self, message):
        """Log com timestamp de Lamport."""
        self.logger.info(message, extra={'timestamp': self.clock.get_time()})
    
    def start(self):
        """Inicia o cliente (servidor gRPC + conexões)."""
        self.log("Inicializando cliente...")
        
        # Conectar ao servidor de impressão burro
        self._connect_to_printer()
        
        # Conectar a outros clientes
        self._connect_to_clients()
        
        # Iniciar servidor gRPC para receber requisições
        self._start_grpc_server()
        
        self.log("Cliente iniciado com sucesso")
        self.log(f"Estado: {self.state.value}")
        self.log(f"Conectado a {len(self.client_stubs)} outros clientes")
    
    def _connect_to_printer(self):
        """Conecta ao servidor de impressão burro."""
        try:
            channel = grpc.insecure_channel(self.server_address)
            self.printer_stub = printing_pb2_grpc.PrintingServiceStub(channel)
            self.log(f"Conectado ao servidor de impressão: {self.server_address}")
        except Exception as e:
            self.log(f"ERRO ao conectar ao servidor: {e}")
            raise
    
    def _connect_to_clients(self):
        """Conecta a outros clientes."""
        for client_addr in self.other_clients:
            try:
                channel = grpc.insecure_channel(client_addr)
                stub = printing_pb2_grpc.MutualExclusionServiceStub(channel)
                self.client_stubs[client_addr] = stub
                self.log(f"Conectado ao cliente: {client_addr}")
            except Exception as e:
                self.log(f"ERRO ao conectar ao cliente {client_addr}: {e}")
    
    def _start_grpc_server(self):
        """Inicia servidor gRPC para receber requisições de outros clientes."""
        self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        printing_pb2_grpc.add_MutualExclusionServiceServicer_to_server(
            self, self.grpc_server
        )
        self.grpc_server.add_insecure_port(f'[::]:{self.port}')
        self.grpc_server.start()
        self.log(f"Servidor gRPC iniciado na porta {self.port}")
    
    # =========================================================================
    # IMPLEMENTAÇÃO DO ALGORITMO DE RICART-AGRAWALA
    # =========================================================================
    
    def request_access(self):
        """
        Solicita acesso ao recurso compartilhado (impressora).
        
        Implementa o protocolo de requisição do Ricart-Agrawala:
        1. Muda estado para WANTED
        2. Incrementa relógio de Lamport
        3. Envia REQUEST para todos os outros clientes
        4. Aguarda OK de todos
        """
        with self.state_lock:
            self.state = ClientState.WANTED
            self.request_number += 1
            self.current_request_timestamp = self.clock.increment()
            
            # Resetar conjunto de respostas pendentes
            with self.replies_lock:
                self.pending_replies = set(self.other_clients)
                if len(self.pending_replies) == 0:
                    # Se não há outros clientes, liberar imediatamente
                    self.all_replies_received.set()
                else:
                    self.all_replies_received.clear()
        
        self.log(f"🔒 Solicitando acesso (req #{self.request_number})")
        self.log(f"Estado: {self.state.value}")
        
        # Enviar REQUEST para todos os outros clientes
        for client_addr, stub in self.client_stubs.items():
            threading.Thread(
                target=self._send_access_request,
                args=(client_addr, stub)
            ).start()
        
        # Aguardar respostas de todos os clientes
        if len(self.other_clients) > 0:
            self.log("Aguardando permissão de todos os clientes...")
        else:
            self.log("Sem outros clientes, acesso direto")
        self.all_replies_received.wait()
        
        # Todas as respostas recebidas, pode entrar na seção crítica
        with self.state_lock:
            self.state = ClientState.HELD
        
        self.log(f"✅ Acesso concedido! Estado: {self.state.value}")
    
    def _send_access_request(self, client_addr, stub):
        """Envia requisição de acesso para um cliente específico."""
        try:
            request = printing_pb2.AccessRequest(
                client_id=self.client_id,
                lamport_timestamp=self.current_request_timestamp,
                request_number=self.request_number
            )
            response = stub.RequestAccess(request, timeout=5.0)
            
            # Atualizar relógio com timestamp da resposta
            self.clock.update(response.lamport_timestamp)
            
            # Remover da lista de respostas pendentes
            with self.replies_lock:
                if client_addr in self.pending_replies:
                    self.pending_replies.remove(client_addr)
                    self.log(f"Permissão recebida de {client_addr} "
                           f"(faltam {len(self.pending_replies)})")
                    
                    # Se todas as respostas foram recebidas
                    if len(self.pending_replies) == 0:
                        self.all_replies_received.set()
        
        except Exception as e:
            self.log(f"ERRO ao solicitar acesso de {client_addr}: {e}")
            # Remover da lista de pendentes mesmo com erro
            with self.replies_lock:
                if client_addr in self.pending_replies:
                    self.pending_replies.remove(client_addr)
                    self.log(f"Removendo {client_addr} dos pendentes devido a erro "
                           f"(faltam {len(self.pending_replies)})")
                    
                    # Se todas as respostas foram recebidas (ou falharam)
                    if len(self.pending_replies) == 0:
                        self.all_replies_received.set()
    
    def _send_release_to_all_clients(self):
        """
        Envia mensagem ReleaseAccess para todos os outros clientes.
        Notifica os outros clientes que o recurso foi liberado.
        """
        self.clock.increment()
        timestamp = self.clock.get_time()
        
        for client_addr in self.other_clients:
            try:
                channel = grpc.insecure_channel(client_addr)
                stub = printing_pb2_grpc.MutualExclusionServiceStub(channel)
                
                release_msg = printing_pb2.AccessRelease(
                    client_id=self.client_id,
                    lamport_timestamp=timestamp,
                    request_number=self.request_number
                )
                
                stub.ReleaseAccess(release_msg, timeout=2.0)
                self.log(f"Enviou ReleaseAccess para {client_addr}")
                
                channel.close()
            except Exception as e:
                self.log(f"Erro ao enviar ReleaseAccess para {client_addr}: {e}")
    
    def release_access(self):
        """
        Libera o acesso ao recurso compartilhado.
        
        Implementa o protocolo de liberação do Ricart-Agrawala:
        1. Muda estado para RELEASED
        2. Libera todos os eventos de requisições adiadas
        3. Envia mensagem ReleaseAccess para todos os outros clientes
        """
        with self.state_lock:
            self.state = ClientState.RELEASED
        
        self.log(f"🔓 Liberando acesso. Estado: {self.state.value}")
        
        # Liberar todas as requisições adiadas (respostas bloqueadas)
        with self.deferred_lock:
            for deferred_request in self.deferred_replies:
                self.log(f"Liberando requisição adiada do cliente {deferred_request['client_id']}")
                deferred_request['event'].set()  # Libera o bloqueio
            
            self.deferred_replies.clear()
        
        # Enviar ReleaseAccess para todos os outros clientes
        self._send_release_to_all_clients()
    
    # =========================================================================
    # IMPLEMENTAÇÃO DOS RPCs (MutualExclusionService)
    # =========================================================================
    
    def RequestAccess(self, request, context):
        """
        RPC: Recebe requisição de acesso de outro cliente.
        
        Lógica do Ricart-Agrawala:
        - Se RELEASED: envia OK imediatamente
        - Se WANTED: compara timestamps e IDs
          - Se minha requisição é mais antiga: adia resposta (bloqueia)
          - Se minha requisição é mais recente: envia OK
        - Se HELD: adia resposta (bloqueia)
        """
        # Atualizar relógio com timestamp recebido
        self.clock.update(request.lamport_timestamp)
        
        self.log(f"📨 Requisição recebida do cliente {request.client_id} "
               f"(TS: {request.lamport_timestamp}, req #{request.request_number})")
        
        # Criar evento para controlar quando responder
        should_defer = threading.Event()
        should_defer.clear()  # Começa bloqueado
        
        with self.state_lock:
            current_state = self.state
            
            # Se RELEASED, enviar OK imediatamente
            if current_state == ClientState.RELEASED:
                self.log(f"→ Enviando OK imediato (estou em RELEASED)")
                response = printing_pb2.AccessResponse(
                    access_granted=True,
                    lamport_timestamp=self.clock.increment()
                )
                return response
            
            # Se HELD, adiar resposta
            elif current_state == ClientState.HELD:
                self.log(f"→ Adiando resposta (estou em HELD)")
                with self.deferred_lock:
                    self.deferred_replies.append({
                        'client_id': request.client_id,
                        'timestamp': request.lamport_timestamp,
                        'request_number': request.request_number,
                        'event': should_defer
                    })
            
            # Se WANTED, comparar timestamps
            elif current_state == ClientState.WANTED:
                comparison = compare_timestamps(
                    self.current_request_timestamp, self.client_id,
                    request.lamport_timestamp, request.client_id
                )
                
                if comparison < 0:
                    # Minha requisição é mais antiga, adiar resposta
                    self.log(f"→ Adiando resposta (minha req é mais antiga: "
                           f"eu={self.current_request_timestamp}/{self.client_id} vs "
                           f"ele={request.lamport_timestamp}/{request.client_id})")
                    with self.deferred_lock:
                        self.deferred_replies.append({
                            'client_id': request.client_id,
                            'timestamp': request.lamport_timestamp,
                            'request_number': request.request_number,
                            'event': should_defer
                        })
                else:
                    # Requisição dele é mais antiga, enviar OK
                    self.log(f"→ Enviando OK (req dele é mais antiga: "
                           f"eu={self.current_request_timestamp}/{self.client_id} vs "
                           f"ele={request.lamport_timestamp}/{request.client_id})")
                    response = printing_pb2.AccessResponse(
                        access_granted=True,
                        lamport_timestamp=self.clock.increment()
                    )
                    return response
        
        # Se chegou aqui, a resposta foi adiada - aguardar liberação
        self.log(f"Aguardando para responder cliente {request.client_id}...")
        should_defer.wait()  # Bloqueia até ser liberado
        
        # Quando liberado, enviar OK
        self.log(f"→ Enviando OK adiado para cliente {request.client_id}")
        response = printing_pb2.AccessResponse(
            access_granted=True,
            lamport_timestamp=self.clock.increment()
        )
        return response
    
    def ReleaseAccess(self, request, context):
        """RPC: Recebe notificação de liberação de outro cliente."""
        self.clock.update(request.lamport_timestamp)
        self.log(f"📨 Cliente {request.client_id} liberou o recurso")
        return printing_pb2.Empty()
    
    # =========================================================================
    # FUNÇÕES DE IMPRESSÃO
    # =========================================================================
    
    def print_message(self, message):
        """
        Envia mensagem para o servidor de impressão burro.
        
        Args:
            message (str): Mensagem a ser impressa
        """
        try:
            request = printing_pb2.PrintRequest(
                client_id=self.client_id,
                message_content=message,
                lamport_timestamp=self.clock.increment(),
                request_number=self.request_number
            )
            
            self.log(f"🖨️  Enviando para impressão: '{message}'")
            response = self.printer_stub.SendToPrinter(request, timeout=10.0)
            
            if response.success:
                self.log(f"✅ {response.confirmation_message}")
            else:
                self.log(f"❌ Falha na impressão")
        
        except Exception as e:
            self.log(f"ERRO ao imprimir: {e}")
    
    def run_printing_cycle(self):
        """
        Executa um ciclo completo de impressão:
        1. Solicita acesso (Ricart-Agrawala)
        2. Imprime mensagem
        3. Libera acesso
        """
        # Solicitar acesso
        self.request_access()
        
        # Seção crítica: imprimir
        message = f"Mensagem {self.request_number} do cliente {self.client_id}"
        self.print_message(message)
        
        # Simular uso do recurso
        time.sleep(0.5)
        
        # Liberar acesso
        self.release_access()
    
    def run(self):
        """Loop principal: gera requisições de impressão automaticamente."""
        self.log("Iniciando loop de requisições automáticas...")
        self.log("Pressione Ctrl+C para encerrar")
        
        try:
            while self.running:
                # Aguardar intervalo aleatório (3-8 segundos)
                interval = random.uniform(3.0, 8.0)
                self.log(f"Próxima requisição em {interval:.2f}s...")
                time.sleep(interval)
                
                # Executar ciclo de impressão
                self.run_printing_cycle()
        
        except KeyboardInterrupt:
            self.log("Encerrando cliente...")
            self.stop()
    
    def stop(self):
        """Para o cliente."""
        self.running = False
        if self.grpc_server:
            self.grpc_server.stop(0)
        self.log("Cliente encerrado")


def main():
    """Função principal do cliente."""
    parser = argparse.ArgumentParser(
        description='Cliente Inteligente - Sistema de Impressão Distribuída'
    )
    parser.add_argument('--id', type=int, required=True,
                       help='ID único do cliente')
    parser.add_argument('--port', type=int, required=True,
                       help='Porta para escutar conexões')
    parser.add_argument('--server', type=str, required=True,
                       help='Endereço do servidor de impressão (ex: localhost:50051)')
    parser.add_argument('--clients', type=str, default='',
                       help='Lista de outros clientes separada por vírgula (ex: localhost:50052,localhost:50053)')
    
    args = parser.parse_args()
    
    # Processar lista de clientes
    other_clients = []
    if args.clients:
        other_clients = [c.strip() for c in args.clients.split(',') if c.strip()]
    
    # Criar e iniciar cliente
    client = PrintingClient(
        client_id=args.id,
        port=args.port,
        server_address=args.server,
        other_clients=other_clients
    )
    
    client.start()
    client.run()


if __name__ == '__main__':
    main()
