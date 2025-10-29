"""
Implementação de Relógios Lógicos de Lamport

Referência: Lamport, Leslie. "Time, clocks, and the ordering of events 
in a distributed system." (1978)

Propriedades:
1. Incremento local: Cada processo incrementa seu relógio antes de cada evento
2. Atualização ao receber mensagem: max(local, received) + 1
3. Ordenação parcial de eventos usando happened-before (→)
"""

import threading


class LamportClock:
    """
    Relógio lógico de Lamport para ordenação de eventos em sistemas distribuídos.
    
    Thread-safe para uso em ambientes concorrentes.
    """
    
    def __init__(self, initial_time=0):
        """
        Inicializa o relógio de Lamport.
        
        Args:
            initial_time (int): Valor inicial do relógio (padrão: 0)
        """
        self._time = initial_time
        self._lock = threading.Lock()
    
    def increment(self):
        """
        Incrementa o relógio local em 1.
        
        Deve ser chamado antes de:
        - Enviar uma mensagem
        - Executar um evento local
        
        Returns:
            int: O novo valor do relógio após incremento
        """
        with self._lock:
            self._time += 1
            return self._time
    
    def update(self, received_time):
        """
        Atualiza o relógio ao receber uma mensagem.
        
        Implementa a regra de Lamport:
        clock = max(local_clock, received_clock) + 1
        
        Args:
            received_time (int): Timestamp recebido na mensagem
            
        Returns:
            int: O novo valor do relógio após atualização
        """
        with self._lock:
            self._time = max(self._time, received_time) + 1
            return self._time
    
    def get_time(self):
        """
        Retorna o valor atual do relógio sem modificá-lo.
        
        Returns:
            int: Valor atual do relógio
        """
        with self._lock:
            return self._time
    
    def __str__(self):
        """String representation do relógio."""
        return f"LamportClock(time={self.get_time()})"
    
    def __repr__(self):
        """Representação oficial do relógio."""
        return self.__str__()


def compare_timestamps(time1, id1, time2, id2):
    """
    Compara dois timestamps de Lamport com desempate por ID.
    
    Usado no algoritmo de Ricart-Agrawala para decidir prioridade
    entre requisições concorrentes.
    
    Regras:
    1. Menor timestamp tem prioridade
    2. Se timestamps iguais, menor ID tem prioridade
    
    Args:
        time1 (int): Timestamp de Lamport do processo 1
        id1 (int): ID do processo 1
        time2 (int): Timestamp de Lamport do processo 2
        id2 (int): ID do processo 2
        
    Returns:
        int: -1 se (time1, id1) < (time2, id2)
              0 se (time1, id1) == (time2, id2)
              1 se (time1, id1) > (time2, id2)
    """
    if time1 < time2:
        return -1
    elif time1 > time2:
        return 1
    else:
        # Timestamps iguais, desempate por ID
        if id1 < id2:
            return -1
        elif id1 > id2:
            return 1
        else:
            return 0


# Exemplo de uso (para testes)
if __name__ == "__main__":
    print("=== Teste do Relógio de Lamport ===\n")
    
    # Criar dois relógios
    clock_a = LamportClock()
    clock_b = LamportClock()
    
    print(f"Clock A inicial: {clock_a}")
    print(f"Clock B inicial: {clock_b}\n")
    
    # Processo A faz evento local
    print("A: Evento local")
    clock_a.increment()
    print(f"Clock A: {clock_a}\n")
    
    # Processo A envia mensagem para B
    print("A: Envia mensagem para B")
    time_sent = clock_a.increment()
    print(f"Clock A: {clock_a}")
    print(f"Timestamp enviado: {time_sent}\n")
    
    # Processo B recebe mensagem de A
    print("B: Recebe mensagem de A")
    clock_b.update(time_sent)
    print(f"Clock B: {clock_b}\n")
    
    # Processo B faz evento local
    print("B: Evento local")
    clock_b.increment()
    print(f"Clock B: {clock_b}\n")
    
    # Teste de comparação de timestamps
    print("=== Teste de Comparação de Timestamps ===\n")
    
    result = compare_timestamps(5, 1, 5, 2)
    print(f"compare_timestamps(5, 1, 5, 2) = {result}")
    print("  (Cliente 1 tem prioridade por menor ID)\n")
    
    result = compare_timestamps(3, 2, 5, 1)
    print(f"compare_timestamps(3, 2, 5, 1) = {result}")
    print("  (Cliente 2 tem prioridade por menor timestamp)")
