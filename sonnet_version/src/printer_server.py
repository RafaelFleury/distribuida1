"""
Servidor de Impressão "Burro"

Características:
- NÃO participa do algoritmo de exclusão mútua
- NÃO conhece outros clientes
- Apenas recebe requisições via gRPC e imprime mensagens
- Simula delay de impressão (2-3 segundos)
- Implementa apenas PrintingService

Porta padrão: 50051
"""

import sys
import time
import random
import argparse
import logging
from concurrent import futures
import os

import grpc

# Ajustar path para imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'generated'))

import printing_pb2
import printing_pb2_grpc


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [SERVIDOR] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class PrinterServer(printing_pb2_grpc.PrintingServiceServicer):
    """
    Implementação do servidor de impressão "burro".
    
    Este servidor apenas:
    1. Recebe requisições de impressão
    2. Imprime mensagens no console
    3. Simula delay de impressão
    4. Retorna confirmação
    """
    
    def __init__(self):
        """Inicializa o servidor de impressão."""
        self.print_count = 0
        logger.info("Servidor de impressão inicializado")
    
    def SendToPrinter(self, request, context):
        """
        Processa uma requisição de impressão.
        
        Args:
            request (PrintRequest): Requisição contendo:
                - client_id: ID do cliente
                - message_content: Conteúdo a ser impresso
                - lamport_timestamp: Timestamp de Lamport
                - request_number: Número da requisição do cliente
            context: Contexto gRPC
            
        Returns:
            PrintResponse: Resposta com confirmação de impressão
        """
        self.print_count += 1
        
        # Log da requisição recebida
        logger.info(f"Requisição recebida do CLIENTE {request.client_id} "
                   f"(req #{request.request_number})")
        
        # Simular tempo de impressão (2-3 segundos)
        delay = random.uniform(2.0, 3.0)
        logger.info(f"Imprimindo... (delay: {delay:.2f}s)")
        
        # Impressão real
        print("\n" + "="*60)
        print(f"[TS: {request.lamport_timestamp}] CLIENTE {request.client_id}: {request.message_content}")
        print("="*60 + "\n")
        
        # Delay para simular impressão
        time.sleep(delay)
        
        # Criar resposta de confirmação
        response = printing_pb2.PrintResponse(
            success=True,
            confirmation_message=f"Impressão #{self.print_count} concluída com sucesso",
            lamport_timestamp=request.lamport_timestamp  # Servidor burro não tem relógio
        )
        
        logger.info(f"Impressão #{self.print_count} concluída para CLIENTE {request.client_id}")
        
        return response


def serve(port):
    """
    Inicia o servidor de impressão na porta especificada.
    
    Args:
        port (int): Porta para escutar conexões (padrão: 50051)
    """
    # Criar servidor gRPC
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Criar instância do servicer para manter referência
    printer_service = PrinterServer()
    
    # Registrar o serviço de impressão
    printing_pb2_grpc.add_PrintingServiceServicer_to_server(
        printer_service, server
    )
    
    # Bind na porta
    server_address = f'[::]:{port}'
    server.add_insecure_port(server_address)
    
    # Iniciar servidor
    server.start()
    
    logger.info("="*60)
    logger.info("🖨️  SERVIDOR DE IMPRESSÃO INICIADO")
    logger.info("="*60)
    logger.info(f"Porta: {port}")
    logger.info(f"Endereço: localhost:{port}")
    logger.info("Aguardando conexões de clientes...")
    logger.info("Pressione Ctrl+C para encerrar")
    logger.info("="*60 + "\n")
    
    try:
        # Manter servidor rodando
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("\n" + "="*60)
        logger.info("🛑 Encerrando servidor...")
        logger.info(f"Total de impressões realizadas: {printer_service.print_count}")
        logger.info("="*60)
        server.stop(0)


def main():
    """Função principal do servidor."""
    parser = argparse.ArgumentParser(
        description='Servidor de Impressão Burro - Sistema Distribuído'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=50051,
        help='Porta para o servidor (padrão: 50051)'
    )
    
    args = parser.parse_args()
    
    # Validar porta
    if args.port < 1024 or args.port > 65535:
        logger.error(f"Porta inválida: {args.port}. Use uma porta entre 1024 e 65535.")
        sys.exit(1)
    
    # Iniciar servidor
    serve(args.port)


if __name__ == '__main__':
    main()
