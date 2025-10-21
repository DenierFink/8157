#!/usr/bin/env python3
"""
Decode display1.csv and show what is being displayed on the LCD.
This file contains the full power-on sequence.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "display1.csv"


def load_data(path: Path) -> List[Tuple[float, Tuple[int, ...]]]:
    """Load CSV data."""
    data = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # Skip header
        
        for row in reader:
            if not row:
                continue
            time = float(row[0])
            states = tuple(int(bit) for bit in row[1:])
            data.append((time, states))
    
    return data


def decode_all_bytes(data: List[Tuple[float, Tuple[int, ...]]]) -> List[Tuple[float, int, bool]]:
    """Decode all bytes: (time, byte_value, is_command)."""
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    # Find clock edges and sample data
    clock_edges = []
    prev_clk = 0
    
    for time, state in post_trigger:
        ch3 = state[3]  # Clock
        
        if prev_clk == 0 and ch3 == 1:  # Rising edge
            ch2 = state[2]  # D/C
            ch4 = state[4]  # Data
            clock_edges.append((time, ch4, ch2))
        
        prev_clk = ch3
    
    # Group into bytes
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


def analyze_display_content(decoded_bytes: List[Tuple[float, int, bool]]) -> None:
    """Analyze and show what's being displayed."""
    
    print("="*80)
    print("DISPLAY CONTENT ANALYSIS - display1.csv")
    print("="*80)
    print(f"\nTotal bytes decoded: {len(decoded_bytes)}")
    
    # Separate commands and data
    commands = [(t, b) for t, b, is_cmd in decoded_bytes if is_cmd]
    data_bytes = [(t, b) for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    print(f"Commands: {len(commands)} bytes")
    print(f"Data: {len(data_bytes)} bytes")
    
    # Show initialization sequence
    print("\n" + "="*80)
    print("INITIALIZATION SEQUENCE")
    print("="*80)
    
    # Find first command sequence
    cmd_sequence = []
    for i, (t, b, is_cmd) in enumerate(decoded_bytes[:50]):
        if is_cmd:
            cmd_sequence.append(f"0x{b:02X}")
        else:
            if cmd_sequence:
                print(f"\nInit commands: {' '.join(cmd_sequence)}")
                cmd_sequence = []
            break
    
    # Analyze data content
    print("\n" + "="*80)
    print("DATA CONTENT - CHARACTER BITMAPS")
    print("="*80)
    
    # Group consecutive data bytes
    data_groups = []
    current_group = []
    
    for t, b, is_cmd in decoded_bytes:
        if not is_cmd:
            current_group.append(b)
        else:
            if current_group:
                data_groups.append(current_group.copy())
                current_group = []
    
    if current_group:
        data_groups.append(current_group)
    
    print(f"\nFound {len(data_groups)} data groups")
    
    # Analyze each group for characters
    for group_idx, group in enumerate(data_groups[:10]):  # First 10 groups
        print(f"\n{'-'*80}")
        print(f"Data Group {group_idx + 1}: {len(group)} bytes")
        
        # Filter out zeros
        non_zero = [b for b in group if b != 0x00]
        
        if non_zero:
            print(f"Non-zero bytes: {len(non_zero)}")
            print(f"Hex: {' '.join(f'0x{b:02X}' for b in non_zero[:20])}")
            if len(non_zero) > 20:
                print(f"     ... +{len(non_zero)-20} more")
            
            # Try to visualize as characters (5-byte columns)
            print("\nAttempting to visualize as characters:")
            visualize_as_characters(non_zero)


def visualize_as_characters(data: List[int], bytes_per_char: int = 5) -> None:
    """Visualize data as character bitmaps."""
    
    # Try to group into characters
    char_count = 0
    i = 0
    
    while i < len(data) and char_count < 10:  # Show first 10 characters
        # Take next bytes_per_char bytes
        char_bytes = data[i:i+bytes_per_char]
        
        if len(char_bytes) < bytes_per_char:
            break
        
        print(f"\n  Character {char_count + 1} (bytes {i}-{i+bytes_per_char-1}):")
        print(f"  Hex: {' '.join(f'0x{b:02X}' for b in char_bytes)}")
        
        # Visualize as vertical columns (common LCD format)
        for row in range(8):
            line = "  "
            for byte_val in char_bytes:
                bit = (byte_val >> row) & 1
                line += "██" if bit else "░░"
            print(line)
        
        # Try to identify the character
        char_id = identify_character(char_bytes)
        if char_id:
            print(f"  → Likely: '{char_id}'")
        
        i += bytes_per_char
        char_count += 1


def identify_character(char_bytes: List[int]) -> str:
    """Try to identify common characters by pattern matching."""
    
    # Convert to tuple for dict key
    pattern = tuple(char_bytes)
    
    # Common 5x8 font patterns
    known_patterns = {
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
    }
    
    return known_patterns.get(pattern, "")


def show_text_content(decoded_bytes: List[Tuple[float, int, bool]]) -> None:
    """Try to extract and show text content."""
    
    print("\n" + "="*80)
    print("ATTEMPTING TO EXTRACT TEXT")
    print("="*80)
    
    # Get all data bytes in order
    data_only = [b for t, b, is_cmd in decoded_bytes if not is_cmd]
    
    # Remove leading/trailing zeros
    start_idx = 0
    for i, b in enumerate(data_only):
        if b != 0x00:
            start_idx = i
            break
    
    end_idx = len(data_only)
    for i in range(len(data_only)-1, -1, -1):
        if data_only[i] != 0x00:
            end_idx = i + 1
            break
    
    relevant_data = data_only[start_idx:end_idx]
    
    print(f"\nRelevant data (excluding leading/trailing zeros): {len(relevant_data)} bytes")
    
    # Try 5-byte character encoding
    print("\nDecoding as 5-byte characters:")
    text = ""
    i = 0
    
    while i < len(relevant_data):
        # Skip zeros
        while i < len(relevant_data) and relevant_data[i] == 0x00:
            i += 1
        
        if i >= len(relevant_data):
            break
        
        # Take 5 bytes for character
        char_bytes = relevant_data[i:i+5]
        
        if len(char_bytes) >= 5:
            char_id = identify_character(char_bytes[:5])
            if char_id:
                text += char_id
            else:
                text += "?"
            i += 5
        else:
            break
    
    if text:
        print(f"\nDecoded text: '{text}'")
    else:
        print("\nCould not decode recognizable text.")
    
    # Show hex dump of relevant data
    print(f"\nHex dump of relevant data (first 100 bytes):")
    for i in range(0, min(100, len(relevant_data)), 10):
        chunk = relevant_data[i:i+10]
        hex_str = ' '.join(f'0x{b:02X}' for b in chunk)
        print(f"  {i:04d}: {hex_str}")


def main():
    print("Loading display1.csv...")
    data = load_data(CAPTURE_PATH)
    print(f"Loaded {len(data)} samples")
    
    print("\nDecoding bytes...")
    decoded_bytes = decode_all_bytes(data)
    print(f"Decoded {len(decoded_bytes)} bytes")
    
    analyze_display_content(decoded_bytes)
    show_text_content(decoded_bytes)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
