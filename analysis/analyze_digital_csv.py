#!/usr/bin/env python3
"""
Extract and analyze text from digital.csv (original file)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Dict

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"

# Extended 5x8 font patterns
CHAR_PATTERNS: Dict[Tuple[int, ...], str] = {
    # Uppercase letters
    (0xF8, 0x24, 0x22, 0x24, 0xF8): 'A',
    (0xFE, 0x92, 0x92, 0x92, 0x6C): 'B',
    (0x7C, 0x82, 0x82, 0x82, 0x44): 'C',
    (0xFE, 0x82, 0x82, 0x82, 0x7C): 'D',
    (0xFE, 0x92, 0x92, 0x92, 0x82): 'E',
    (0xFE, 0x12, 0x12, 0x12, 0x02): 'F',
    (0x7C, 0x82, 0x92, 0x92, 0x74): 'G',
    (0xFE, 0x10, 0x10, 0x10, 0xFE): 'H',
    (0x00, 0x82, 0xFE, 0x82, 0x00): 'I',
    (0x40, 0x80, 0x80, 0x80, 0x7E): 'J',
    (0xFE, 0x10, 0x28, 0x44, 0x82): 'K',
    (0xFE, 0x80, 0x80, 0x80, 0x80): 'L',
    (0xFE, 0x04, 0x08, 0x04, 0xFE): 'M',
    (0xFE, 0x04, 0x08, 0x10, 0xFE): 'N',
    (0x7C, 0x82, 0x82, 0x82, 0x7C): 'O',
    (0xFE, 0x12, 0x12, 0x12, 0x0C): 'P',
    (0x7C, 0x82, 0x8A, 0x84, 0x78): 'Q',
    (0xFE, 0x12, 0x32, 0x52, 0x8C): 'R',
    (0x4C, 0x92, 0x92, 0x92, 0x64): 'S',
    (0x02, 0x02, 0xFE, 0x02, 0x02): 'T',
    (0x7E, 0x80, 0x80, 0x80, 0x7E): 'U',
    (0x3E, 0x40, 0x80, 0x40, 0x3E): 'V',
    (0xFE, 0x40, 0x30, 0x40, 0xFE): 'W',
    (0xC6, 0x28, 0x10, 0x28, 0xC6): 'X',
    (0x06, 0x08, 0xF0, 0x08, 0x06): 'Y',
    (0xC2, 0xA2, 0x92, 0x8A, 0x86): 'Z',
    # Numbers
    (0x7C, 0xA2, 0x92, 0x8A, 0x7C): '0',
    (0x00, 0x84, 0xFE, 0x80, 0x00): '1',
    (0xC4, 0xA2, 0x92, 0x92, 0x8C): '2',
    (0x44, 0x92, 0x92, 0x92, 0x6C): '3',
    (0x1E, 0x10, 0x10, 0xFE, 0x10): '4',
    (0x4E, 0x92, 0x92, 0x92, 0x62): '5',
    (0x7C, 0x92, 0x92, 0x92, 0x64): '6',
    (0x02, 0x02, 0xE2, 0x12, 0x0E): '7',
    (0x6C, 0x92, 0x92, 0x92, 0x6C): '8',
    (0x4C, 0x92, 0x92, 0x92, 0x7C): '9',
    # Special
    (0x00, 0x00, 0x00, 0x00, 0x00): ' ',
    (0x00, 0x00, 0xFA, 0x00, 0x00): '!',
    (0x80, 0x80, 0x80, 0x80, 0x80): '-',
    (0x00, 0x00, 0x80, 0x00, 0x00): '.',
    (0x40, 0x20, 0x10, 0x08, 0x04): '/',
    (0x08, 0x08, 0x08, 0x08, 0x08): ':',
}


def load_and_decode(path: Path) -> List[Tuple[float, int, bool]]:
    """Load and decode bytes."""
    data = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for row in reader:
            if not row:
                continue
            time = float(row[0])
            states = tuple(int(bit) for bit in row[1:])
            data.append((time, states))
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    clock_edges = []
    prev_clk = 0
    
    for time, state in post_trigger:
        ch3 = state[3]
        if prev_clk == 0 and ch3 == 1:
            ch2 = state[2]
            ch4 = state[4]
            clock_edges.append((time, ch4, ch2))
        prev_clk = ch3
    
    decoded_bytes = []
    current_byte_bits = []
    
    for time, data_bit, dc in clock_edges:
        current_byte_bits.append((data_bit, dc, time))
        if len(current_byte_bits) == 8:
            byte_val = 0
            for i, (bit, _, _) in enumerate(current_byte_bits):
                byte_val |= (bit << (7 - i))
            dc_flag = current_byte_bits[0][1]
            byte_time = current_byte_bits[0][2]
            decoded_bytes.append((byte_time, byte_val, dc_flag == 0))
            current_byte_bits = []
    
    return decoded_bytes


def analyze_digital_csv():
    """Analyze digital.csv for display content."""
    
    print("="*80)
    print("ANÁLISE COMPLETA - digital.csv")
    print("="*80)
    
    decoded_bytes = load_and_decode(CAPTURE_PATH)
    print(f"\nTotal bytes decodificados: {len(decoded_bytes)}")
    
    # Separate commands and data
    commands = [(t, b) for t, b, is_cmd in decoded_bytes if is_cmd]
    data_only = [(t, b) for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    print(f"Comandos: {len(commands)} bytes")
    print(f"Dados: {len(data_only)} bytes")
    
    # Show initialization
    print("\n" + "="*80)
    print("SEQUÊNCIA DE INICIALIZAÇÃO")
    print("="*80)
    
    init_cmds = [b for t, b, is_cmd in decoded_bytes[:20] if is_cmd]
    print(f"\nPrimeiros comandos: {' '.join(f'0x{b:02X}' for b in init_cmds[:15])}")
    
    # Find non-zero data sequences
    print("\n" + "="*80)
    print("PROCURANDO TEXTO E CARACTERES")
    print("="*80)
    
    sequences = []
    current_seq = []
    seq_start_time = None
    
    for t, b in data_only:
        if b != 0x00:
            if not current_seq:
                seq_start_time = t
            current_seq.append(b)
        else:
            if len(current_seq) >= 5:
                sequences.append((seq_start_time, current_seq.copy()))
            current_seq = []
    
    if len(current_seq) >= 5:
        sequences.append((seq_start_time, current_seq))
    
    print(f"\nEncontradas {len(sequences)} sequências não-zero (≥5 bytes)")
    
    # Try to decode each sequence
    all_text = []
    
    for seq_idx, (start_time, seq_data) in enumerate(sequences):
        decoded_chars = []
        i = 0
        
        while i < len(seq_data):
            found = False
            
            # Try 5-byte pattern
            if i + 5 <= len(seq_data):
                pattern = tuple(seq_data[i:i+5])
                if pattern in CHAR_PATTERNS:
                    char = CHAR_PATTERNS[pattern]
                    decoded_chars.append((char, i, pattern))
                    i += 5
                    found = True
            
            if not found:
                # Try next byte
                if i + 5 <= len(seq_data):
                    pattern = tuple(seq_data[i:i+5])
                    decoded_chars.append(('?', i, pattern))
                    i += 5
                else:
                    i += 1
        
        if decoded_chars:
            text = ''.join([c[0] for c in decoded_chars])
            recognized_chars = [(c, p, pat) for c, p, pat in decoded_chars if c != '?']
            
            if recognized_chars:
                all_text.append((start_time, text, decoded_chars))
                
                print(f"\n{'-'*80}")
                print(f"Sequência {seq_idx + 1} @ t={start_time:.3f}s")
                print(f"Texto decodificado: '{text}'")
                
                for char, pos, pattern in recognized_chars:
                    print(f"  [{pos:3d}] '{char}' = {' '.join(f'0x{b:02X}' for b in pattern)}")
                    
                    # Show bitmap for recognized chars
                    if char in ['A', 'F', 'B', 'C', 'D', 'E']:
                        print(f"       Bitmap de '{char}':")
                        for row in range(8):
                            line = "       "
                            for byte_val in pattern:
                                bit = (byte_val >> row) & 1
                                line += "██" if bit else "░░"
                            print(line)
    
    # Summary
    print("\n" + "="*80)
    print("RESUMO - TEXTO COMPLETO")
    print("="*80)
    
    if all_text:
        print("\nTodos os caracteres identificados:")
        for start_time, text, chars in all_text:
            recognized = ''.join([c for c, _, _ in chars if c != '?'])
            if recognized:
                print(f"  t={start_time:7.3f}s: '{recognized}'")
        
        # Full text
        all_chars = []
        for _, text, chars in all_text:
            all_chars.extend([c for c, _, _ in chars if c != '?'])
        
        print(f"\n{'='*80}")
        print(f"TEXTO FINAL DO DISPLAY: '{' '.join(all_chars)}'")
        print(f"{'='*80}")
    else:
        print("\nNenhum caractere reconhecido encontrado.")
    
    # Show data statistics
    print("\n" + "="*80)
    print("ESTATÍSTICAS DOS DADOS")
    print("="*80)
    
    data_values = [b for t, b in data_only]
    non_zero = [b for b in data_values if b != 0x00]
    
    print(f"\nTotal de bytes de dados: {len(data_values)}")
    print(f"Bytes não-zero: {len(non_zero)} ({100*len(non_zero)/len(data_values):.1f}%)")
    print(f"Valores únicos não-zero: {len(set(non_zero))}")
    
    # Most common bytes
    from collections import Counter
    counter = Counter(non_zero)
    print("\nBytes não-zero mais comuns:")
    for byte_val, count in counter.most_common(15):
        char = CHAR_PATTERNS.get((byte_val, 0, 0, 0, 0), '')
        print(f"  0x{byte_val:02X} ({byte_val:3d}): {count:3d}x")


def main():
    print("Carregando e decodificando digital.csv...")
    analyze_digital_csv()
    
    print("\n" + "="*80)
    print("ANÁLISE COMPLETA!")
    print("="*80)


if __name__ == "__main__":
    main()
