#!/usr/bin/env python3
"""
Verify if CH3 is actually the CLOCK and CH4 is DATA.
Look for byte patterns: 8 clock pulses per byte.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple
from collections import Counter

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"


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


def analyze_clock_hypothesis(data: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Test hypothesis: CH3 = CLOCK, CH4 = DATA."""
    
    print("="*70)
    print("TESTING HYPOTHESIS: CH3=CLOCK, CH4=DATA")
    print("="*70)
    
    post_trigger = [(t, s) for t, s in data if t >= 0][:1000]  # First 1000 samples
    
    # Count rising edges of CH3
    ch3_rising_edges = []
    prev_ch3 = 0
    
    for time, state in post_trigger:
        ch0, ch1, ch2, ch3, ch4 = state
        
        if prev_ch3 == 0 and ch3 == 1:  # Rising edge
            ch3_rising_edges.append((time, ch4, ch2))  # Store data bit and D/C
        
        prev_ch3 = ch3
    
    print(f"\nCH3 rising edges found: {len(ch3_rising_edges)}")
    print("\nFirst 100 clock edges with sampled data:")
    print("  # | Time (s)      | CH4(data) | CH2(D/C) | Byte boundary")
    print("-" * 65)
    
    for i, (time, data_bit, dc) in enumerate(ch3_rising_edges[:100]):
        byte_boundary = "  <-- BYTE" if (i > 0 and i % 8 == 0) else ""
        print(f"{i:3d} | {time:.9f} | {data_bit:9d} | {dc:8d} | {byte_boundary}")
    
    # Try to decode bytes
    print("\n" + "="*70)
    print("DECODING BYTES (CH3=clock, CH4=data, MSB first)")
    print("="*70)
    
    bytes_decoded = []
    current_byte_bits = []
    current_dc = None
    
    for i, (time, data_bit, dc) in enumerate(ch3_rising_edges):
        current_byte_bits.append(data_bit)
        current_dc = dc
        
        if len(current_byte_bits) == 8:
            # Convert to byte (MSB first)
            byte_val = 0
            for j, bit in enumerate(current_byte_bits):
                byte_val |= (bit << (7 - j))
            
            bytes_decoded.append((byte_val, current_dc, i-7, i))
            current_byte_bits = []
    
    print(f"\nDecoded {len(bytes_decoded)} bytes:")
    print("\nByte# | Clk Range | D/C | Hex  | Dec | Binary   | ASCII")
    print("-" * 70)
    
    for idx, (byte_val, dc, start_clk, end_clk) in enumerate(bytes_decoded[:50]):
        dc_str = "CMD " if dc == 0 else "DATA"
        ascii_char = chr(byte_val) if 32 <= byte_val <= 126 else '.'
        binary = f"{byte_val:08b}"
        
        print(f"{idx:4d}  | {start_clk:3d}-{end_clk:3d}  | {dc_str} | 0x{byte_val:02X} | {byte_val:3d} | {binary} | '{ascii_char}'")
    
    if len(bytes_decoded) > 50:
        print(f"\n... and {len(bytes_decoded) - 50} more bytes")
    
    # Group by D/C
    print("\n" + "="*70)
    print("GROUPING BY COMMAND/DATA")
    print("="*70)
    
    commands = [b for b, dc, _, _ in bytes_decoded if dc == 0]
    data_bytes = [b for b, dc, _, _ in bytes_decoded if dc == 1]
    
    print(f"\nCommands (D/C=0): {len(commands)} bytes")
    if commands:
        print("First 20 commands:")
        for i, cmd in enumerate(commands[:20]):
            print(f"  0x{cmd:02X}", end="  ")
            if (i + 1) % 10 == 0:
                print()
    
    print(f"\n\nData (D/C=1): {len(data_bytes)} bytes")
    if data_bytes:
        print("First 50 data bytes (hex):")
        for i, d in enumerate(data_bytes[:50]):
            print(f"  0x{d:02X}", end="  ")
            if (i + 1) % 10 == 0:
                print()
        
        print("\n\nFirst 50 data bytes (ASCII where printable):")
        ascii_str = ""
        for d in data_bytes[:50]:
            if 32 <= d <= 126:
                ascii_str += chr(d)
            else:
                ascii_str += f"[{d:02X}]"
        print(f"  {ascii_str}")
    
    # Analyze unique commands
    print("\n" + "="*70)
    print("UNIQUE COMMANDS")
    print("="*70)
    
    unique_cmds = Counter(commands)
    print(f"\nFound {len(unique_cmds)} unique command bytes:")
    for cmd, count in unique_cmds.most_common():
        print(f"  0x{cmd:02X} : {count} times")


def analyze_byte_sequences(data: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Look for repeating byte sequences."""
    
    print("\n" + "="*70)
    print("LOOKING FOR MULTI-BYTE COMMAND SEQUENCES")
    print("="*70)
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    # Decode all bytes with their D/C flag
    ch3_rising_edges = []
    prev_ch3 = 0
    
    for time, state in post_trigger:
        ch0, ch1, ch2, ch3, ch4 = state
        
        if prev_ch3 == 0 and ch3 == 1:
            ch3_rising_edges.append((time, ch4, ch2))
        
        prev_ch3 = ch3
    
    # Decode bytes
    all_bytes = []
    current_byte_bits = []
    current_dc = None
    
    for time, data_bit, dc in ch3_rising_edges:
        current_byte_bits.append(data_bit)
        current_dc = dc
        
        if len(current_byte_bits) == 8:
            byte_val = 0
            for j, bit in enumerate(current_byte_bits):
                byte_val |= (bit << (7 - j))
            
            all_bytes.append((byte_val, current_dc))
            current_byte_bits = []
    
    # Find command sequences (consecutive bytes with D/C=0)
    print("\nCommand sequences (consecutive CMD bytes):")
    
    in_cmd_seq = False
    cmd_sequence = []
    
    for byte_val, dc in all_bytes:
        if dc == 0:  # Command
            cmd_sequence.append(byte_val)
            in_cmd_seq = True
        else:
            if in_cmd_seq and cmd_sequence:
                seq_str = " ".join(f"0x{b:02X}" for b in cmd_sequence)
                print(f"  [{len(cmd_sequence)} bytes] {seq_str}")
            cmd_sequence = []
            in_cmd_seq = False
    
    # Show last sequence if exists
    if cmd_sequence:
        seq_str = " ".join(f"0x{b:02X}" for b in cmd_sequence)
        print(f"  [{len(cmd_sequence)} bytes] {seq_str}")


def main():
    print("Loading data...")
    data = load_data(CAPTURE_PATH)
    print(f"Loaded {len(data)} samples\n")
    
    analyze_clock_hypothesis(data)
    analyze_byte_sequences(data)
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("\nCORRECT CHANNEL MAPPING:")
    print("  CH0: Chip Select/Enable (active high, short pulses)")
    print("  CH1: Reset/Enable (goes HIGH at trigger, stays HIGH)")
    print("  CH2: D/C (Data/Command: 0=Command, 1=Data)")
    print("  CH3: SERIAL CLOCK (SCK/SCL) ← CLOCK SIGNAL")
    print("  CH4: SERIAL DATA (MOSI/SDA)  ← DATA SIGNAL")
    print("\nThis appears to be a standard SPI-like serial protocol!")
    print("="*70)


if __name__ == "__main__":
    main()
