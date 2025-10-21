#!/usr/bin/env python3
"""
Analisa os sinais de controle (CS, RST, D/C) e o timing da inicialização.
Identifica a sequência exata de power-on e configuração do display.
"""

import csv
import sys

# Mapeamento dos canais
CH_CS = 0    # Chip Select
CH_RST = 1   # Reset
CH_DC = 2    # Data/Command
CH_SCK = 3   # Serial Clock
CH_MOSI = 4  # Data

def load_csv(filename):
    """Carrega o CSV do Saleae Logic"""
    data = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        for row in reader:
            if len(row) >= 6:
                time = float(row[0])
                channels = [int(row[i+1]) for i in range(5)]
                data.append((time, channels))
    
    return data

def analyze_control_timing(data):
    """Analisa o timing dos sinais de controle"""
    print("=" * 70)
    print("ANÁLISE DE SINAIS DE CONTROLE")
    print("=" * 70)
    print()
    
    # Estado inicial
    prev_cs = data[0][1][CH_CS]
    prev_rst = data[0][1][CH_RST]
    prev_dc = data[0][1][CH_DC]
    prev_sck = data[0][1][CH_SCK]
    prev_mosi = data[0][1][CH_MOSI]
    
    print(f"Estado inicial (t=0):")
    print(f"  CS:   {'HIGH' if prev_cs else 'LOW'}")
    print(f"  RST:  {'HIGH' if prev_rst else 'LOW'}")
    print(f"  D/C:  {'HIGH' if prev_dc else 'LOW'}")
    print(f"  SCK:  {'HIGH' if prev_sck else 'LOW'}")
    print(f"  MOSI: {'HIGH' if prev_mosi else 'LOW'}")
    print()
    
    # Detectar transições importantes
    print("Transições importantes:")
    print("-" * 70)
    
    rst_transitions = []
    cs_transitions = []
    first_clock = None
    
    for i, (time, channels) in enumerate(data):
        cs, rst, dc, sck, mosi = channels
        
        # Transições de RST
        if rst != prev_rst:
            rst_transitions.append((time, rst))
            print(f"t={time:9.6f}s: RST {prev_rst} → {rst} ({'LOW→HIGH' if rst else 'HIGH→LOW'})")
        
        # Transições de CS
        if cs != prev_cs:
            cs_transitions.append((time, cs))
            if len(cs_transitions) <= 5:  # Primeiras 5 transições
                print(f"t={time:9.6f}s: CS  {prev_cs} → {cs} ({'LOW→HIGH' if cs else 'HIGH→LOW'})")
        
        # Primeiro clock depois do reset alto
        if first_clock is None and rst == 1 and sck != prev_sck:
            first_clock = time
            print(f"t={time:9.6f}s: Primeiro clock após RST HIGH")
        
        prev_cs = cs
        prev_rst = rst
        prev_dc = dc
        prev_sck = sck
        prev_mosi = mosi
    
    print()
    print("=" * 70)
    print("TIMING CRÍTICO")
    print("=" * 70)
    
    if len(rst_transitions) >= 2:
        rst_low_time = rst_transitions[0][0]
        rst_high_time = rst_transitions[1][0]
        rst_pulse_width = rst_high_time - rst_low_time
        
        print(f"\nPulso de RESET:")
        print(f"  Início (LOW): t={rst_low_time:.6f}s")
        print(f"  Fim (HIGH):   t={rst_high_time:.6f}s")
        print(f"  Duração:      {rst_pulse_width*1000:.2f} ms")
        
        if first_clock:
            delay_after_rst = first_clock - rst_high_time
            print(f"\nDelay RST HIGH → Primeiro clock: {delay_after_rst*1000:.2f} ms")
    
    if len(cs_transitions) > 0:
        print(f"\nTotal de transições CS: {len(cs_transitions)}")
        print(f"Primeira ativação CS: t={cs_transitions[0][0]:.6f}s")

def decode_first_transaction(data):
    """Decodifica a primeira transação após reset"""
    print()
    print("=" * 70)
    print("PRIMEIRA TRANSAÇÃO APÓS RESET")
    print("=" * 70)
    print()
    
    # Encontrar quando RST vai HIGH
    rst_high_idx = 0
    for i, (time, channels) in enumerate(data):
        if channels[CH_RST] == 1:
            rst_high_idx = i
            break
    
    # Encontrar primeira transação (CS LOW)
    first_cs_low = None
    for i in range(rst_high_idx, len(data)):
        time, channels = data[i]
        if channels[CH_CS] == 0:
            first_cs_low = i
            print(f"Primeira ativação CS em t={time:.6f}s")
            break
    
    if first_cs_low is None:
        print("Nenhuma transação encontrada!")
        return
    
    # Decodificar bytes até CS HIGH
    bytes_decoded = []
    current_byte = 0
    bit_count = 0
    prev_sck = data[first_cs_low][1][CH_SCK]
    dc_level = data[first_cs_low][1][CH_DC]
    
    for i in range(first_cs_low, min(first_cs_low + 1000, len(data))):
        time, channels = data[i]
        cs, rst, dc, sck, mosi = channels
        
        if cs == 1:  # CS voltou HIGH, fim da transação
            if bit_count > 0:
                bytes_decoded.append((dc_level, current_byte))
            break
        
        # Detectar borda de subida do clock (amostragem)
        if sck == 1 and prev_sck == 0:
            current_byte = (current_byte << 1) | mosi
            bit_count += 1
            
            if bit_count == 8:
                bytes_decoded.append((dc_level, current_byte))
                current_byte = 0
                bit_count = 0
                dc_level = dc  # Atualizar D/C para próximo byte
        
        prev_sck = sck
    
    print(f"\nBytes decodificados (primeira transação):")
    for i, (dc, byte_val) in enumerate(bytes_decoded):
        dc_str = "DATA" if dc else "CMD "
        print(f"  [{i:2d}] {dc_str}: 0x{byte_val:02X}")
    
    print()
    print("Sequência de inicialização (apenas comandos):")
    init_seq = [f"0x{b:02X}" for dc, b in bytes_decoded if dc == 0]
    print("  " + ", ".join(init_seq))

def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'digital.csv'
    
    print(f"Carregando {csv_file}...")
    data = load_csv(csv_file)
    print(f"Carregadas {len(data)} amostras\n")
    
    analyze_control_timing(data)
    decode_first_transaction(data)

if __name__ == '__main__':
    main()
