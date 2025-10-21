#!/usr/bin/env python3
"""
Visualize character bitmaps found in the data stream.
"""

def visualize_byte_as_bitmap(byte_val: int, bit_order='MSB') -> str:
    """Convert a byte to visual bitmap."""
    bits = f"{byte_val:08b}"
    if bit_order == 'LSB':
        bits = bits[::-1]
    
    visual = ""
    for bit in bits:
        visual += "██" if bit == '1' else "░░"
    return visual


def analyze_character_data():
    """Analyze the character data found at t=4.348s."""
    
    print("="*60)
    print("CHARACTER BITMAP ANALYSIS")
    print("="*60)
    
    # Character data from t=4.348s
    char1_data = [0xF8, 0x24, 0x22, 0x24, 0xF8]
    char2_data = [0x31, 0x49, 0x49]
    
    print("\nFirst character (5 bytes):")
    print("Hex: " + " ".join(f"0x{b:02X}" for b in char1_data))
    print("\nBinary visualization (MSB first):")
    for i, byte_val in enumerate(char1_data):
        binary = f"{byte_val:08b}"
        visual = visualize_byte_as_bitmap(byte_val, 'MSB')
        print(f"  Byte {i}: {binary}  {visual}  (0x{byte_val:02X})")
    
    print("\n" + "-"*60)
    print("\nSecond character (3 bytes):")
    print("Hex: " + " ".join(f"0x{b:02X}" for b in char2_data))
    print("\nBinary visualization (MSB first):")
    for i, byte_val in enumerate(char2_data):
        binary = f"{byte_val:08b}"
        visual = visualize_byte_as_bitmap(byte_val, 'MSB')
        print(f"  Byte {i}: {binary}  {visual}  (0x{byte_val:02X})")
    
    # Try to visualize as 5x7 or 8x8 font
    print("\n" + "="*60)
    print("POSSIBLE CHARACTER SHAPES")
    print("="*60)
    
    print("\nCharacter 1 - Rotated view (common LCD format):")
    # In many LCDs, bytes are vertical columns
    for row in range(8):
        line = ""
        for byte_val in char1_data:
            bit = (byte_val >> row) & 1
            line += "██" if bit else "░░"
        print(f"  Row {row}: {line}")
    
    print("\nCharacter 2 - Rotated view:")
    for row in range(8):
        line = ""
        for byte_val in char2_data:
            bit = (byte_val >> row) & 1
            line += "██" if bit else "░░"
        print(f"  Row {row}: {line}")
    
    # More data from the second sequence at t=4.423s
    print("\n" + "="*60)
    print("MORE CHARACTER DATA (t=4.423s)")
    print("="*60)
    
    more_data = [0x12, 0x11, 0x12, 0x7C, 0x00, 0x18, 0xA4, 0xA4, 0xA4, 0x7C]
    
    print("\nHex sequence:")
    print(" ".join(f"0x{b:02X}" for b in more_data))
    
    print("\nVisualized as vertical columns (5 chars × 2 bytes?):")
    for row in range(8):
        line = ""
        for i, byte_val in enumerate(more_data):
            bit = (byte_val >> row) & 1
            line += "██" if bit else "░░"
            # Add separator every 5 bytes
            if (i + 1) % 5 == 0:
                line += "  "
        print(f"  Row {row}: {line}")
    
    print("\n" + "="*60)
    print("\n💡 INTERPRETATION:")
    print("   The data appears to be font bitmap data for characters.")
    print("   Each byte represents a vertical column of pixels.")
    print("   Common format for small LCDs (5x7 or 5x8 fonts).")
    print("   The display likely shows numbers or text.")
    print("="*60)


if __name__ == "__main__":
    analyze_character_data()
