#!/usr/bin/env python3
"""
Create a visual timeline of the LCD communication.
Shows commands, data blocks, and timing.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"


def load_and_decode(path: Path) -> List[Tuple[float, int, bool, str]]:
    """Load and decode to (time, byte_value, is_command, hex_str) format."""
    
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
    
    # Decode bytes
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
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
            
            decoded_bytes.append((byte_time, byte_val, dc_flag == 0, f"0x{byte_val:02X}"))
            current_byte_bits = []
    
    return decoded_bytes


def create_visual_timeline(decoded_bytes: List[Tuple[float, int, bool, str]]) -> None:
    """Create ASCII art timeline of communication."""
    
    print("\n" + "="*80)
    print("VISUAL TIMELINE - LCD COMMUNICATION")
    print("="*80)
    print("\nLegend:")
    print("  [CMD] = Command byte (D/C=0)")
    print("  {DAT} = Data byte (D/C=1)")
    print("  Time shown in seconds from trigger")
    print("-"*80)
    
    # Group consecutive same-type bytes
    groups = []
    current_group = []
    current_type = None
    group_start = None
    
    for time, byte_val, is_cmd, hex_str in decoded_bytes:
        if current_type is None or is_cmd != current_type:
            if current_group:
                groups.append((group_start, current_group[0][0], current_type, current_group))
            current_group = [(time, byte_val, hex_str)]
            current_type = is_cmd
            group_start = time
        else:
            current_group.append((time, byte_val, hex_str))
    
    if current_group:
        groups.append((group_start, current_group[0][0], current_type, current_group))
    
    # Display timeline
    for i, (start_time, first_time, is_cmd, bytes_list) in enumerate(groups):
        type_marker = "[CMD]" if is_cmd else "{DAT}"
        count = len(bytes_list)
        
        # Show time marker
        time_str = f"t={start_time:7.3f}s"
        
        # Byte preview (first 10)
        preview_bytes = bytes_list[:10]
        preview = " ".join(b[2] for b in preview_bytes)
        if len(bytes_list) > 10:
            preview += f" ... +{len(bytes_list)-10} more"
        
        # Create visual bar
        bar_length = min(count, 60)
        bar_char = "█" if is_cmd else "░"
        bar = bar_char * bar_length
        
        print(f"\n{time_str} {type_marker} [{count:4d} bytes]")
        print(f"  {bar}")
        print(f"  {preview}")
        
        # Special annotation for first command
        if i == 0 and is_cmd:
            print(f"  ↑ INITIALIZATION SEQUENCE")


def show_byte_patterns(decoded_bytes: List[Tuple[float, int, bool, str]]) -> None:
    """Show common byte patterns in the data."""
    
    print("\n" + "="*80)
    print("BYTE PATTERN ANALYSIS")
    print("="*80)
    
    # Count byte frequencies
    cmd_bytes = {}
    data_bytes = {}
    
    for time, byte_val, is_cmd, hex_str in decoded_bytes:
        if is_cmd:
            cmd_bytes[byte_val] = cmd_bytes.get(byte_val, 0) + 1
        else:
            data_bytes[byte_val] = data_bytes.get(byte_val, 0) + 1
    
    print("\nCommand bytes frequency:")
    for byte_val in sorted(cmd_bytes.keys()):
        count = cmd_bytes[byte_val]
        bar = "▓" * min(count, 40)
        print(f"  0x{byte_val:02X} ({byte_val:3d}): {bar} {count}")
    
    print("\nData bytes frequency (top 20):")
    sorted_data = sorted(data_bytes.items(), key=lambda x: x[1], reverse=True)[:20]
    for byte_val, count in sorted_data:
        bar = "░" * min(count // 10, 40)
        ascii_char = chr(byte_val) if 32 <= byte_val <= 126 else '.'
        print(f"  0x{byte_val:02X} ({byte_val:3d}) '{ascii_char}': {bar} {count}")


def main():
    print("Loading and decoding...")
    decoded_bytes = load_and_decode(CAPTURE_PATH)
    print(f"Decoded {len(decoded_bytes)} bytes total")
    
    create_visual_timeline(decoded_bytes)
    show_byte_patterns(decoded_bytes)
    
    print("\n" + "="*80)
    print("TIMELINE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
