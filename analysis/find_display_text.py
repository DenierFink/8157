#!/usr/bin/env python3
"""
Advanced decoder for display1.csv - find actual displayed content.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple
from collections import Counter

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "display1.csv"


def load_and_decode(path: Path) -> List[Tuple[float, int, bool]]:
    """Load and decode to bytes."""
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


def find_interesting_data(decoded_bytes: List[Tuple[float, int, bool]]) -> None:
    """Find non-zero data sequences that might be characters."""
    
    print("="*80)
    print("SEARCHING FOR ACTUAL DISPLAY CONTENT")
    print("="*80)
    
    # Get only data bytes
    data_only = [(t, b) for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    print(f"\nTotal data bytes: {len(data_only)}")
    
    # Find sequences of non-zero bytes
    sequences = []
    current_seq = []
    
    for t, b in data_only:
        if b != 0x00:
            current_seq.append((t, b))
        else:
            if len(current_seq) >= 5:  # At least 5 bytes
                sequences.append(current_seq.copy())
            current_seq = []
    
    if len(current_seq) >= 5:
        sequences.append(current_seq)
    
    print(f"Found {len(sequences)} non-zero sequences (≥5 bytes)")
    
    # Analyze each sequence
    for idx, seq in enumerate(sequences[:20]):  # First 20 sequences
        print(f"\n{'='*80}")
        print(f"Sequence {idx + 1}: {len(seq)} bytes @ t={seq[0][0]:.3f}s")
        print(f"{'='*80}")
        
        bytes_only = [b for t, b in seq]
        
        # Show hex
        hex_str = ' '.join(f'0x{b:02X}' for b in bytes_only[:30])
        if len(bytes_only) > 30:
            hex_str += f" ... +{len(bytes_only)-30} more"
        print(f"Hex: {hex_str}")
        
        # Try to decode as characters (5-byte columns)
        print("\nVisualizing as characters (5 bytes per char):")
        visualize_sequence(bytes_only)


def visualize_sequence(data: List[int]) -> None:
    """Visualize a sequence as character bitmaps."""
    
    # Known character patterns (5x8 font)
    char_patterns = {
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
    
    decoded_text = ""
    i = 0
    
    while i < len(data):
        # Try different character widths
        for width in [5, 6, 4]:  # Common font widths
            if i + width <= len(data):
                char_bytes = tuple(data[i:i+width])
                
                # Pad with zeros if needed for matching
                if width < 5:
                    char_bytes = char_bytes + (0x00,) * (5 - width)
                elif width > 5:
                    char_bytes = char_bytes[:5]
                
                if char_bytes in char_patterns:
                    char = char_patterns[char_bytes]
                    decoded_text += char
                    
                    print(f"\n  Char {len(decoded_text)}: '{char}' @ byte {i}")
                    print(f"  Hex: {' '.join(f'0x{b:02X}' for b in data[i:i+width])}")
                    
                    # Show bitmap
                    for row in range(8):
                        line = "  "
                        for byte_val in data[i:i+width]:
                            bit = (byte_val >> row) & 1
                            line += "██" if bit else "░░"
                        print(line)
                    
                    i += width
                    break
        else:
            # No match, try next byte
            i += 1
    
    if decoded_text:
        print(f"\n{'='*80}")
        print(f"DECODED TEXT: '{decoded_text}'")
        print(f"{'='*80}")
    
    # Also try viewing as raw bitmap
    if len(data) >= 10 and not decoded_text:
        print("\nViewing as raw bitmap (first 50 bytes):")
        for row in range(8):
            line = ""
            for byte_val in data[:min(50, len(data))]:
                bit = (byte_val >> row) & 1
                line += "█" if bit else "░"
            print(f"  Row {row}: {line}")


def main():
    print("Loading display1.csv...")
    decoded_bytes = load_and_decode(CAPTURE_PATH)
    print(f"Decoded {len(decoded_bytes)} bytes")
    
    find_interesting_data(decoded_bytes)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
