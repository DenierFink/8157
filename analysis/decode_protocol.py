#!/usr/bin/env python3
"""
Decode the LCD protocol based on identified channels:
- CH0: Chip Select / Enable
- CH1: Reset/Enable (trigger)
- CH2: D/C (Data=1 / Command=0)
- CH3: Serial Data (MOSI/SDA)
- CH4: Serial Clock (SCK/SCL)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"


@dataclass
class Transaction:
    """Represents a single transaction to the LCD."""
    start_time: float
    end_time: float
    is_command: bool  # True if command (D/C=0), False if data (D/C=1)
    bits: List[int]
    bytes_hex: List[str]
    chip_select_active: bool


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


def decode_serial_data(data: List[Tuple[float, Tuple[int, ...]]]) -> List[Transaction]:
    """
    Decode serial data by sampling on clock edges.
    CH3 = Data line
    CH4 = Clock line
    CH2 = D/C (0=command, 1=data)
    CH0 = Chip Select
    """
    transactions = []
    
    # Focus on post-trigger data
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    if not post_trigger:
        return transactions
    
    # Detect clock edges and sample data
    prev_clk = 0
    current_bits = []
    current_dc = None
    transaction_start = None
    prev_dc = None
    
    for i, (time, state) in enumerate(post_trigger):
        ch0, ch1, ch2, ch3, ch4 = state
        
        # Detect D/C changes (start of new transaction)
        if prev_dc is not None and ch2 != prev_dc and current_bits:
            # Save previous transaction
            bytes_hex = bits_to_bytes(current_bits)
            transactions.append(Transaction(
                start_time=transaction_start,
                end_time=time,
                is_command=(prev_dc == 0),
                bits=current_bits.copy(),
                bytes_hex=bytes_hex,
                chip_select_active=False
            ))
            current_bits = []
            transaction_start = None
        
        # Sample on rising edge of clock
        if prev_clk == 0 and ch4 == 1:
            if transaction_start is None:
                transaction_start = time
            current_bits.append(ch3)
            current_dc = ch2
        
        prev_clk = ch4
        prev_dc = ch2
    
    # Save last transaction
    if current_bits and current_dc is not None:
        bytes_hex = bits_to_bytes(current_bits)
        transactions.append(Transaction(
            start_time=transaction_start,
            end_time=post_trigger[-1][0],
            is_command=(current_dc == 0),
            bits=current_bits,
            bytes_hex=bytes_hex,
            chip_select_active=False
        ))
    
    return transactions


def bits_to_bytes(bits: List[int]) -> List[str]:
    """Convert list of bits to hex bytes (MSB first)."""
    bytes_hex = []
    
    # Pad to multiple of 8
    while len(bits) % 8 != 0:
        bits = bits + [0]
    
    # Convert each 8 bits to a byte
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        byte_val = 0
        for j, bit in enumerate(byte_bits):
            byte_val |= (bit << (7 - j))
        bytes_hex.append(f"0x{byte_val:02X}")
    
    return bytes_hex


def analyze_timing(data: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Analyze timing characteristics."""
    print("\n" + "="*70)
    print("TIMING ANALYSIS")
    print("="*70)
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    # Find clock period
    clock_edges = []
    prev_clk = 0
    
    for time, state in post_trigger:
        ch4 = state[4]
        if prev_clk == 0 and ch4 == 1:  # Rising edge
            clock_edges.append(time)
        prev_clk = ch4
    
    if len(clock_edges) > 1:
        periods = [clock_edges[i+1] - clock_edges[i] for i in range(len(clock_edges)-1)]
        if periods:
            avg_period = sum(periods) / len(periods)
            freq = 1.0 / avg_period if avg_period > 0 else 0
            
            print(f"\nClock Signal (CH4):")
            print(f"  Total clock edges: {len(clock_edges)}")
            print(f"  Average period: {avg_period*1e6:.2f} µs")
            print(f"  Frequency: {freq/1e3:.2f} kHz")
            print(f"  Bit rate: {freq/1e3:.2f} kbps")


def main():
    print("="*70)
    print("LCD PROTOCOL DECODER")
    print("="*70)
    print("\nChannel mapping:")
    print("  CH0: Chip Select/Enable")
    print("  CH1: Reset/Enable (trigger)")
    print("  CH2: D/C (0=Command, 1=Data)")
    print("  CH3: Serial Data (MOSI)")
    print("  CH4: Serial Clock (SCK)")
    
    print("\nLoading capture data...")
    data = load_data(CAPTURE_PATH)
    print(f"Loaded {len(data)} samples")
    
    analyze_timing(data)
    
    print("\n" + "="*70)
    print("DECODING TRANSACTIONS")
    print("="*70)
    
    transactions = decode_serial_data(data)
    print(f"\nFound {len(transactions)} transactions")
    
    # Group consecutive same-type transactions
    print("\n" + "-"*70)
    
    for i, trans in enumerate(transactions[:50]):  # Show first 50
        duration_ms = (trans.end_time - trans.start_time) * 1000
        type_str = "CMD " if trans.is_command else "DATA"
        
        print(f"\n[{i:03d}] {type_str} @ t={trans.start_time:.6f}s (duration: {duration_ms:.3f}ms)")
        print(f"      Bits: {len(trans.bits)}")
        print(f"      Bytes: {' '.join(trans.bytes_hex)}")
        
        # Try to show ASCII if it looks like data
        if not trans.is_command and trans.bytes_hex:
            try:
                ascii_chars = []
                for hex_str in trans.bytes_hex:
                    byte_val = int(hex_str, 16)
                    if 32 <= byte_val <= 126:  # Printable ASCII
                        ascii_chars.append(chr(byte_val))
                    else:
                        ascii_chars.append('.')
                if ascii_chars:
                    print(f"      ASCII: {''.join(ascii_chars)}")
            except:
                pass
    
    if len(transactions) > 50:
        print(f"\n... and {len(transactions) - 50} more transactions")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    cmd_count = sum(1 for t in transactions if t.is_command)
    data_count = sum(1 for t in transactions if not t.is_command)
    
    print(f"\nTotal transactions: {len(transactions)}")
    print(f"  Commands: {cmd_count}")
    print(f"  Data: {data_count}")
    
    # Show unique commands
    unique_commands = set()
    for t in transactions:
        if t.is_command:
            unique_commands.add(' '.join(t.bytes_hex))
    
    print(f"\nUnique commands ({len(unique_commands)}):")
    for cmd in sorted(unique_commands)[:20]:
        print(f"  {cmd}")
    
    if len(unique_commands) > 20:
        print(f"  ... and {len(unique_commands) - 20} more")


if __name__ == "__main__":
    main()
