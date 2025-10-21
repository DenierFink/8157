#!/usr/bin/env python3
"""
Extrai TODA a sequência de inicialização da nova captura.
Decodifica todas as transações desde o reset até estabilizar.
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

def decode_all_transactions(data):
    """Decodifica todas as transações"""
    
    # Encontrar quando RST vai HIGH (início real)
    rst_high_idx = 0
    for i, (time, channels) in enumerate(data):
        if channels[CH_RST] == 1:
            rst_high_idx = i
            print(f"RST vai HIGH em t={time:.6f}s (índice {i})")
            break
    
    # Decodificar todas as transações
    transactions = []
    i = rst_high_idx
    
    while i < len(data):
        time, channels = data[i]
        cs = channels[CH_CS]
        
        # Procurar CS LOW (início de transação)
        if cs == 0:
            trans_start_time = time
            trans_bytes = []
            current_byte = 0
            bit_count = 0
            prev_sck = channels[CH_SCK]
            dc_level = channels[CH_DC]
            
            # Decodificar até CS HIGH
            while i < len(data):
                time, channels = data[i]
                cs, rst, dc, sck, mosi = channels
                
                if cs == 1:  # Fim da transação
                    if bit_count > 0:
                        trans_bytes.append((dc_level, current_byte))
                    if trans_bytes:
                        transactions.append((trans_start_time, trans_bytes))
                    break
                
                # Borda de subida do clock = amostra o dado
                if sck == 1 and prev_sck == 0:
                    current_byte = (current_byte << 1) | mosi
                    bit_count += 1
                    
                    if bit_count == 8:
                        trans_bytes.append((dc_level, current_byte))
                        current_byte = 0
                        bit_count = 0
                        dc_level = dc
                
                prev_sck = sck
                i += 1
        
        i += 1
    
    return transactions

def print_init_sequence(transactions, limit=10):
    """Imprime as primeiras transações (sequência de init)"""
    print()
    print("=" * 70)
    print(f"SEQUÊNCIA DE INICIALIZAÇÃO (primeiras {limit} transações)")
    print("=" * 70)
    print()
    
    all_commands = []
    
    for idx, (time, bytes_list) in enumerate(transactions[:limit]):
        print(f"[{idx:2d}] t={time:9.6f}s ({len(bytes_list):2d} bytes)")
        
        cmd_line = "  CMD: "
        data_line = "  DATA:"
        has_cmd = False
        has_data = False
        
        for dc, byte_val in bytes_list:
            if dc == 0:  # Comando
                cmd_line += f" 0x{byte_val:02X}"
                all_commands.append(byte_val)
                has_cmd = True
            else:  # Dado
                data_line += f" 0x{byte_val:02X}"
                has_data = True
        
        if has_cmd:
            print(cmd_line)
        if has_data:
            print(data_line)
        print()
    
    print("=" * 70)
    print("SEQUÊNCIA DE COMANDOS PARA CÓDIGO ESP32")
    print("=" * 70)
    print()
    print("// Sequência de inicialização extraída da captura")
    print("static const uint8_t INIT_SEQUENCE[] = {")
    
    # Quebrar em linhas de 12 bytes
    for i in range(0, len(all_commands), 12):
        chunk = all_commands[i:i+12]
        hex_str = ", ".join([f"0x{b:02X}" for b in chunk])
        if i + 12 < len(all_commands):
            print(f"  {hex_str},")
        else:
            print(f"  {hex_str}")
    
    print("};")
    print()
    print(f"Total: {len(all_commands)} bytes de comandos")

def interpret_command(cmd):
    """Interpreta comandos conhecidos"""
    if cmd == 0xA2 or cmd == 0xA3:
        return f"LCD Bias (1/{9 if cmd == 0xA2 else 7})"
    elif cmd == 0xA0 or cmd == 0xA1:
        return f"ADC Select (normal/reverse)"
    elif cmd == 0xC0 or cmd == 0xC8:
        return f"COM Scan Direction"
    elif cmd == 0xAF:
        return "Display ON"
    elif cmd == 0xAE:
        return "Display OFF"
    elif (cmd & 0xF0) == 0x40:
        return f"Display Start Line: {cmd & 0x3F}"
    elif cmd == 0x81:
        return "Set Contrast (next byte = value)"
    elif (cmd & 0xF0) == 0x20:
        return f"Resistor Ratio: {cmd & 0x07}"
    elif (cmd & 0xF0) == 0xB0:
        return f"Set Page: {cmd & 0x0F}"
    elif (cmd & 0xF0) == 0x10:
        return f"Set Column MSB: {cmd & 0x0F}"
    elif (cmd & 0xF0) == 0x00:
        return f"Set Column LSB: {cmd & 0x0F}"
    else:
        return "Unknown"

def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'digital.csv'
    
    print(f"Carregando {csv_file}...")
    data = load_csv(csv_file)
    print(f"Carregadas {len(data)} amostras")
    print()
    
    transactions = decode_all_transactions(data)
    print(f"\nTotal de transações decodificadas: {len(transactions)}")
    
    print_init_sequence(transactions, limit=15)
    
    # Interpretar primeiros comandos
    print()
    print("=" * 70)
    print("INTERPRETAÇÃO DOS PRIMEIROS COMANDOS")
    print("=" * 70)
    print()
    
    for idx, (time, bytes_list) in enumerate(transactions[:5]):
        print(f"Transação {idx}:")
        for dc, byte_val in bytes_list:
            if dc == 0:  # Apenas comandos
                interp = interpret_command(byte_val)
                print(f"  0x{byte_val:02X} - {interp}")
        print()

if __name__ == '__main__':
    main()
