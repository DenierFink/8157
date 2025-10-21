#!/usr/bin/env python3
"""
Complete LCD Protocol Decoder
Final channel mapping confirmed:
- CH0: Chip Select/Enable
- CH1: Reset/Enable (trigger)
- CH2: D/C (0=Command, 1=Data)
- CH3: Serial Clock (SCK)
- CH4: Serial Data (MOSI)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"


@dataclass
class Transaction:
    """A transaction is a sequence of bytes with same D/C flag."""
    start_time: float
    end_time: float
    is_command: bool
    bytes: List[int]
    
    def __str__(self):
        hex_str = " ".join(f"0x{b:02X}" for b in self.bytes)
        type_str = "CMD " if self.is_command else "DATA"
        duration_ms = (self.end_time - self.start_time) * 1000
        return f"{type_str} [{len(self.bytes):2d} bytes] @ t={self.start_time:.6f}s ({duration_ms:.2f}ms): {hex_str}"


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


def decode_transactions(data: List[Tuple[float, Tuple[int, ...]]]) -> List[Transaction]:
    """Decode all transactions from the capture."""
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    # Step 1: Find all clock rising edges and sample data
    clock_edges = []
    prev_clk = 0
    
    for time, state in post_trigger:
        ch0, ch1, ch2, ch3, ch4 = state
        
        # Rising edge of clock (CH3)
        if prev_clk == 0 and ch3 == 1:
            clock_edges.append((time, ch4, ch2))  # (time, data_bit, dc_flag)
        
        prev_clk = ch3
    
    # Step 2: Group into bytes (8 bits each, MSB first)
    byte_stream = []
    current_byte_bits = []
    
    for time, data_bit, dc in clock_edges:
        current_byte_bits.append((data_bit, dc, time))
        
        if len(current_byte_bits) == 8:
            # Convert to byte
            byte_val = 0
            for i, (bit, _, _) in enumerate(current_byte_bits):
                byte_val |= (bit << (7 - i))
            
            dc_flag = current_byte_bits[0][1]  # D/C from first bit
            byte_time = current_byte_bits[0][2]
            
            byte_stream.append((byte_val, dc_flag, byte_time))
            current_byte_bits = []
    
    # Step 3: Group into transactions (consecutive bytes with same D/C)
    transactions = []
    current_trans_bytes = []
    current_dc = None
    trans_start = None
    trans_end = None
    
    for byte_val, dc, time in byte_stream:
        if current_dc is None or dc != current_dc:
            # Save previous transaction
            if current_trans_bytes:
                transactions.append(Transaction(
                    start_time=trans_start,
                    end_time=trans_end,
                    is_command=(current_dc == 0),
                    bytes=current_trans_bytes.copy()
                ))
            
            # Start new transaction
            current_trans_bytes = [byte_val]
            current_dc = dc
            trans_start = time
            trans_end = time
        else:
            current_trans_bytes.append(byte_val)
            trans_end = time
    
    # Save last transaction
    if current_trans_bytes:
        transactions.append(Transaction(
            start_time=trans_start,
            end_time=trans_end,
            is_command=(current_dc == 0),
            bytes=current_trans_bytes
        ))
    
    return transactions


def analyze_lcd_commands(transactions: List[Transaction]) -> None:
    """Analyze command patterns to identify LCD controller."""
    
    print("\n" + "="*70)
    print("LCD COMMAND ANALYSIS")
    print("="*70)
    
    # Collect all command sequences
    command_sequences = [t for t in transactions if t.is_command]
    
    print(f"\nFound {len(command_sequences)} command sequences:")
    print("\n" + "-"*70)
    
    for i, trans in enumerate(command_sequences):
        print(f"[{i:02d}] {trans}")
        
        # Try to identify common LCD commands
        if len(trans.bytes) >= 1:
            cmd = trans.bytes[0]
            interpretation = interpret_lcd_command(cmd, trans.bytes)
            if interpretation:
                print(f"     → {interpretation}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("STATISTICS")
    print("="*70)
    
    total_commands = sum(len(t.bytes) for t in transactions if t.is_command)
    total_data = sum(len(t.bytes) for t in transactions if not t.is_command)
    
    print(f"\nTotal command bytes: {total_commands}")
    print(f"Total data bytes: {total_data}")
    print(f"Total transactions: {len(transactions)}")
    
    # Unique command bytes
    unique_cmds = set()
    for t in transactions:
        if t.is_command:
            unique_cmds.update(t.bytes)
    
    print(f"\nUnique command bytes ({len(unique_cmds)}):")
    for cmd in sorted(unique_cmds):
        print(f"  0x{cmd:02X} ({cmd:3d}) - {interpret_single_cmd(cmd)}")


def interpret_lcd_command(cmd: int, full_sequence: List[int]) -> Optional[str]:
    """Try to interpret LCD command based on common patterns."""
    
    # Common patterns for various LCD controllers
    interpretations = {
        0x01: "Display Clear / Software Reset",
        0x11: "Sleep Out",
        0x13: "Normal Display Mode On",
        0x20: "Display Inversion OFF",
        0x21: "Display Inversion ON",
        0x28: "Display OFF",
        0x29: "Display ON",
        0x2A: "Column Address Set",
        0x2B: "Page Address Set",
        0x2C: "Memory Write",
        0x36: "Memory Access Control",
        0x3A: "Pixel Format Set",
        0xB0: "RAM Address Set",
        0xC0: "Panel Driving Setting",
        0xC5: "VCOM Control",
        0xD1: "Set Oscillator",
        0xE0: "Positive Gamma Control",
        0xE1: "Negative Gamma Control",
        0xAF: "Display ON",
        0xA5: "Display All Points ON",
        0xA0: "Segment Remap",
        0x57: "Brightness Control",
    }
    
    base_interp = interpretations.get(cmd, "Unknown")
    
    if len(full_sequence) > 1:
        params = " ".join(f"0x{b:02X}" for b in full_sequence[1:])
        return f"{base_interp} (params: {params})"
    else:
        return base_interp


def interpret_single_cmd(cmd: int) -> str:
    """Quick interpretation of single command byte."""
    interpretations = {
        0x01: "Clear/Reset", 0x11: "Sleep Out", 0x13: "Normal Mode",
        0x20: "Invert OFF", 0x21: "Invert ON", 0x28: "Display OFF",
        0x29: "Display ON", 0x2A: "Col Addr", 0x2B: "Row Addr",
        0x2C: "Mem Write", 0x36: "Mem Access", 0x3A: "Pixel Format",
        0xB0: "RAM Addr", 0xC0: "Panel Drive", 0xC5: "VCOM Ctrl",
        0xD1: "Oscillator", 0xE0: "Gamma+", 0xE1: "Gamma-",
        0xAF: "Disp ON", 0xA5: "All Pts ON", 0xA0: "Seg Remap",
        0x57: "Brightness", 0x50: "Sleep?", 0x22: "All Pixels OFF?",
        0x85: "Power Ctrl?", 0xEB: "Internal?", 0x02: "Addr?",
        0xBD: "Config?", 0xC4: "Timing?", 0x40: "Start Line?",
        0x0A: "Config?", 0xF4: "Internal?", 0x0B: "Config?",
        0x21: "Invert", 0x00: "NOP?", 0xCC: "Config?",
        0x16: "Config?", 0x82: "Config?", 0x5E: "Config?",
        0x81: "Contrast?", 0x6A: "Config?", 0x20: "?",
        0x5F: "Config?", 0x45: "Config?", 0x43: "Config?",
        0x80: "Config?", 0x4B: "Config?", 0x2A: "Col Addr?",
        0x08: "Config?", 0x59: "Config?", 0x88: "Config?",
        0x90: "Config?", 0xB2: "Config?", 0x10: "Config?",
        0x2C: "Mem Write?", 0xFA: "Config?", 0x1C: "Config?",
        0x58: "Config?", 0x52: "Config?", 0x60: "Config?",
    }
    return interpretations.get(cmd, "Unknown")


def export_results(transactions: List[Transaction], output_path: Path) -> None:
    """Export decoded results to a file."""
    
    with output_path.open('w', encoding='utf-8') as f:
        f.write("LCD COMMUNICATION DECODE RESULTS\n")
        f.write("="*70 + "\n\n")
        
        f.write("Channel Mapping:\n")
        f.write("  CH0: Chip Select/Enable\n")
        f.write("  CH1: Reset/Enable (trigger)\n")
        f.write("  CH2: D/C (0=Command, 1=Data)\n")
        f.write("  CH3: Serial Clock (SCK)\n")
        f.write("  CH4: Serial Data (MOSI)\n\n")
        
        f.write(f"Total Transactions: {len(transactions)}\n")
        f.write("="*70 + "\n\n")
        
        for i, trans in enumerate(transactions):
            f.write(f"Transaction {i:03d}:\n")
            f.write(f"  {trans}\n")
            
            if trans.is_command and len(trans.bytes) >= 1:
                interp = interpret_lcd_command(trans.bytes[0], trans.bytes)
                if interp:
                    f.write(f"  → {interp}\n")
            
            f.write("\n")


def main():
    print("="*70)
    print("LCD PROTOCOL COMPLETE DECODER")
    print("="*70)
    
    print("\nLoading data...")
    data = load_data(CAPTURE_PATH)
    print(f"Loaded {len(data)} samples")
    
    print("\nDecoding transactions...")
    transactions = decode_transactions(data)
    print(f"Decoded {len(transactions)} transactions")
    
    # Analyze commands
    analyze_lcd_commands(transactions)
    
    # Export results
    output_file = CAPTURE_PATH.parent / "decoded_lcd_protocol.txt"
    export_results(transactions, output_file)
    print(f"\n\nResults exported to: {output_file}")
    
    print("\n" + "="*70)
    print("DECODING COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
