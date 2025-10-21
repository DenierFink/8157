#!/usr/bin/env python3
"""
Analisa os níveis IDLE dos sinais (quando não há comunicação ativa).
Identifica o estado de repouso correto de cada linha.
"""

import csv
import sys

CH_CS = 0
CH_RST = 1
CH_DC = 2
CH_SCK = 3
CH_MOSI = 4

def load_csv(filename):
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

def analyze_idle_levels(data):
    """Analisa os níveis quando CS está HIGH (sem comunicação)"""
    print("=" * 70)
    print("ANÁLISE DE NÍVEIS IDLE (CS = HIGH, sem comunicação)")
    print("=" * 70)
    print()
    
    # Coletar amostras quando CS está HIGH
    idle_samples = []
    
    for time, channels in data:
        cs = channels[CH_CS]
        if cs == 1:  # CS HIGH = sem comunicação ativa
            idle_samples.append(channels)
    
    if not idle_samples:
        print("Nenhuma amostra idle encontrada!")
        return
    
    # Contar frequência de cada nível
    rst_high = sum(1 for s in idle_samples if s[CH_RST] == 1)
    dc_high = sum(1 for s in idle_samples if s[CH_DC] == 1)
    sck_high = sum(1 for s in idle_samples if s[CH_SCK] == 1)
    mosi_high = sum(1 for s in idle_samples if s[CH_MOSI] == 1)
    
    total = len(idle_samples)
    
    print(f"Total de amostras IDLE (CS=HIGH): {total}")
    print()
    print("Níveis predominantes quando IDLE:")
    print(f"  RST:  {'HIGH' if rst_high > total/2 else 'LOW':4s} ({rst_high/total*100:5.1f}% HIGH)")
    print(f"  D/C:  {'HIGH' if dc_high > total/2 else 'LOW':4s} ({dc_high/total*100:5.1f}% HIGH)")
    print(f"  SCK:  {'HIGH' if sck_high > total/2 else 'LOW':4s} ({sck_high/total*100:5.1f}% HIGH)")
    print(f"  MOSI: {'HIGH' if mosi_high > total/2 else 'LOW':4s} ({mosi_high/total*100:5.1f}% HIGH)")
    
    print()
    print("=" * 70)
    print("RECOMENDAÇÃO PARA O CÓDIGO ESP32")
    print("=" * 70)
    print()
    print("Configurar níveis IDLE como:")
    print(f"  lcdCS(HIGH);      // CS sempre HIGH quando idle")
    print(f"  lcdRST({'HIGH' if rst_high > total/2 else 'LOW':4s});     // RST idle = {'HIGH' if rst_high > total/2 else 'LOW'}")
    print(f"  lcdDC({'HIGH' if dc_high > total/2 else 'LOW':4s});      // D/C idle = {'HIGH' if dc_high > total/2 else 'LOW'}")
    print(f"  lcdSCK({'HIGH' if sck_high > total/2 else 'LOW':4s});     // SCK idle = {'HIGH' if sck_high > total/2 else 'LOW'}")
    print(f"  lcdMOSI({'HIGH' if mosi_high > total/2 else 'LOW':4s});   // MOSI idle = {'HIGH' if mosi_high > total/2 else 'LOW'}")

def analyze_active_levels(data):
    """Analisa os níveis durante comunicação ativa (CS=LOW)"""
    print()
    print("=" * 70)
    print("ANÁLISE DURANTE COMUNICAÇÃO ATIVA (CS = LOW)")
    print("=" * 70)
    print()
    
    # Pegar primeiras 100 amostras com CS LOW para ver início da comunicação
    active_samples = []
    for time, channels in data:
        if channels[CH_CS] == 0:
            active_samples.append((time, channels))
            if len(active_samples) >= 100:
                break
    
    if not active_samples:
        print("Nenhuma comunicação ativa encontrada!")
        return
    
    print(f"Primeiras amostras com CS=LOW (início da comunicação):")
    print()
    print("Time(s)    CS RST D/C SCK MOSI")
    print("-" * 35)
    
    for i in range(min(10, len(active_samples))):
        time, ch = active_samples[i]
        print(f"{time:9.6f}  {ch[0]}  {ch[1]}   {ch[2]}   {ch[3]}   {ch[4]}")
    
    # Verificar estado do clock durante comunicação
    sck_states = [ch[CH_SCK] for _, ch in active_samples]
    sck_high_pct = sum(sck_states) / len(sck_states) * 100
    
    print()
    print(f"Durante CS=LOW (comunicação):")
    print(f"  SCK HIGH: {sck_high_pct:.1f}% do tempo")
    print(f"  → Clock idle durante byte: {'HIGH' if sck_high_pct > 50 else 'LOW'}")

def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'digital.csv'
    
    print(f"Carregando {csv_file}...")
    data = load_csv(csv_file)
    print(f"Carregadas {len(data)} amostras\n")
    
    analyze_idle_levels(data)
    analyze_active_levels(data)

if __name__ == '__main__':
    main()
