#!/usr/bin/env python3
"""
Complete text extraction from display1.csv
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Dict

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "display1.csv"

# Extended 5x8 font patterns (common LCD fonts)
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


def extract_all_text(decoded_bytes: List[Tuple[float, int, bool]]) -> None:
    """Extract all text from the data."""
    
    print("="*80)
    print("EXTRACTING ALL TEXT FROM DISPLAY")
    print("="*80)
    
    # Get all data bytes with timing
    data_only = [(t, b) for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    # Find all non-zero sequences
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
            seq_start_time = None
    
    if len(current_seq) >= 5:
        sequences.append((seq_start_time, current_seq))
    
    print(f"\nFound {len(sequences)} data sequences")
    print("\nAttempting to decode all characters:\n")
    
    all_text = []
    
    for seq_idx, (start_time, seq_data) in enumerate(sequences):
        decoded_chars = []
        i = 0
        
        while i < len(seq_data):
            found = False
            
            # Try 5-byte pattern first (most common)
            if i + 5 <= len(seq_data):
                pattern = tuple(seq_data[i:i+5])
                if pattern in CHAR_PATTERNS:
                    char = CHAR_PATTERNS[pattern]
                    decoded_chars.append((char, i, pattern))
                    i += 5
                    found = True
            
            if not found:
                # Show unknown pattern
                if i + 5 <= len(seq_data):
                    pattern = tuple(seq_data[i:i+5])
                    decoded_chars.append(('?', i, pattern))
                    i += 5
                else:
                    i += 1
        
        if decoded_chars:
            text = ''.join([c[0] for c in decoded_chars])
            all_text.append((start_time, text, decoded_chars))
            
            print(f"Sequence {seq_idx + 1} @ t={start_time:.3f}s: '{text}'")
            
            # Show details for recognized characters
            for char, pos, pattern in decoded_chars:
                if char != '?':
                    print(f"  [{pos:3d}] '{char}' = {' '.join(f'0x{b:02X}' for b in pattern)}")
    
    # Summary
    print("\n" + "="*80)
    print("ALL DECODED TEXT")
    print("="*80)
    
    for start_time, text, _ in all_text:
        if any(c != '?' for c in text):
            print(f"t={start_time:7.3f}s: '{text}'")
    
    # Full concatenated text
    all_chars = ''.join([text for _, text, _ in all_text])
    recognized = [c for c in all_chars if c != '?']
    
    print(f"\nTotal recognized characters: {len(recognized)}")
    if recognized:
        print(f"Characters: {' '.join(recognized)}")


def show_byte_statistics(decoded_bytes: List[Tuple[float, int, bool]]) -> None:
    """Show statistics about the data."""
    
    print("\n" + "="*80)
    print("DATA STATISTICS")
    print("="*80)
    
    data_only = [b for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    non_zero = [b for b in data_only if b != 0x00]
    print(f"\nTotal data bytes: {len(data_only)}")
    print(f"Non-zero bytes: {len(non_zero)} ({100*len(non_zero)/len(data_only):.1f}%)")
    
    # Unique non-zero values
    unique_vals = set(non_zero)
    print(f"Unique non-zero values: {len(unique_vals)}")
    
    # Most common non-zero bytes
    from collections import Counter
    counter = Counter(non_zero)
    print("\nMost common non-zero bytes:")
    for byte_val, count in counter.most_common(20):
        print(f"  0x{byte_val:02X} ({byte_val:3d}): {count:4d} times")


def main():
    print("Loading and decoding display1.csv...")
    decoded_bytes = load_and_decode(CAPTURE_PATH)
    print(f"Decoded {len(decoded_bytes)} total bytes\n")
    
    extract_all_text(decoded_bytes)
    show_byte_statistics(decoded_bytes)
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
