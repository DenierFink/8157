#!/usr/bin/env python3
"""
Identify the actual function of each channel by analyzing behavior patterns.
No assumptions about protocol - pure data-driven analysis.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import List, Tuple

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"


def load_data(path: Path) -> List[Tuple[float, Tuple[int, ...]]]:
    """Load CSV data."""
    data = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        print(f"CSV Header: {header}\n")
        
        for row in reader:
            if not row:
                continue
            time = float(row[0])
            states = tuple(int(bit) for bit in row[1:])
            data.append((time, states))
    
    return data


def analyze_channel_behavior(data: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Analyze each channel's behavior to identify its function."""
    
    print("="*70)
    print("CHANNEL BEHAVIOR ANALYSIS")
    print("="*70)
    
    # Split into pre-trigger and post-trigger
    pre_trigger = [(t, s) for t, s in data if t < 0]
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    print(f"\nPre-trigger samples: {len(pre_trigger)}")
    print(f"Post-trigger samples: {len(post_trigger)}")
    print(f"Trigger point: t=0.0s (Channel 1 goes HIGH)")
    
    num_channels = len(data[0][1]) if data else 0
    
    for ch in range(num_channels):
        print(f"\n{'='*70}")
        print(f"CHANNEL {ch}")
        print(f"{'='*70}")
        
        # Count transitions
        transitions = []
        prev_state = None
        
        for time, state in data:
            bit = state[ch]
            if prev_state is not None and bit != prev_state:
                transitions.append((time, prev_state, bit))
            prev_state = bit
        
        print(f"\nTotal transitions: {len(transitions)}")
        
        # Transitions before and after trigger
        pre_trans = [t for t in transitions if t[0] < 0]
        post_trans = [t for t in transitions if t[0] >= 0]
        
        print(f"  Before trigger (t<0): {len(pre_trans)}")
        print(f"  After trigger (t≥0): {len(post_trans)}")
        
        # State at key moments
        if pre_trigger:
            first_state = pre_trigger[0][1][ch]
            print(f"\nState at start (t={pre_trigger[0][0]:.6f}s): {first_state}")
        
        # State right before trigger
        pre_trigger_state = None
        for t, s in reversed(pre_trigger):
            if t < 0:
                pre_trigger_state = s[ch]
                break
        if pre_trigger_state is not None:
            print(f"State just before trigger (t<0): {pre_trigger_state}")
        
        # State right after trigger
        if post_trigger:
            post_trigger_state = post_trigger[0][1][ch]
            print(f"State at trigger (t=0): {post_trigger_state}")
        
        # Dominant state
        high_count = sum(1 for _, s in post_trigger if s[ch] == 1)
        low_count = len(post_trigger) - high_count
        print(f"\nPost-trigger state distribution:")
        print(f"  HIGH: {high_count} samples ({100*high_count/len(post_trigger):.1f}%)")
        print(f"  LOW: {low_count} samples ({100*low_count/len(post_trigger):.1f}%)")
        
        # Show first few transitions
        if transitions:
            print(f"\nFirst 10 transitions:")
            for i, (time, from_st, to_st) in enumerate(transitions[:10]):
                marker = "★ TRIGGER" if -0.001 < time < 0.001 else ""
                print(f"  {i+1}. t={time:+.6f}s  {from_st}→{to_st}  {marker}")
        
        # Pulse width analysis (post-trigger only)
        if post_trans:
            high_pulses = []
            low_pulses = []
            
            in_high = None
            in_low = None
            
            for time, state in post_trigger:
                bit = state[ch]
                
                if bit == 1:
                    if in_low is not None:
                        low_pulses.append(time - in_low)
                        in_low = None
                    if in_high is None:
                        in_high = time
                else:
                    if in_high is not None:
                        high_pulses.append(time - in_high)
                        in_high = None
                    if in_low is None:
                        in_low = time
            
            if high_pulses:
                print(f"\nHIGH pulse widths (post-trigger):")
                print(f"  Count: {len(high_pulses)}")
                print(f"  Min: {min(high_pulses)*1e6:.2f} µs")
                print(f"  Max: {max(high_pulses)*1e6:.2f} µs")
                print(f"  Median: {median(high_pulses)*1e6:.2f} µs")
                print(f"  Mean: {mean(high_pulses)*1e6:.2f} µs")
                
                # Show distribution of common values
                pulse_ranges = Counter()
                for p in high_pulses:
                    # Bucket into 0.1µs ranges
                    bucket = round(p * 1e6, 1)
                    pulse_ranges[bucket] += 1
                
                if len(pulse_ranges) <= 10:
                    print(f"  Distribution: {dict(pulse_ranges.most_common())}")
            
            if low_pulses and len(low_pulses) > 1:
                print(f"\nLOW pulse widths (post-trigger):")
                print(f"  Count: {len(low_pulses)}")
                print(f"  Min: {min(low_pulses)*1e6:.2f} µs")
                print(f"  Max: {max(low_pulses)*1e6:.2f} µs")
                print(f"  Median: {median(low_pulses)*1e6:.2f} µs")


def analyze_correlations(data: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Look for correlations between channels."""
    print(f"\n{'='*70}")
    print("CHANNEL CORRELATIONS")
    print(f"{'='*70}")
    
    post_trigger = [(t, s) for t, s in data if t >= 0]
    
    if not post_trigger:
        return
    
    num_channels = len(post_trigger[0][1])
    
    # Look at transitions: when one channel changes, what happens to others?
    print("\nWhen each channel transitions, do others change too?")
    
    for ch in range(num_channels):
        transitions = []
        prev_state = None
        
        for time, state in post_trigger:
            bit = state[ch]
            if prev_state is not None and bit != prev_state:
                transitions.append((time, state))
            prev_state = bit
        
        if not transitions:
            continue
        
        print(f"\nChannel {ch} transitions ({len(transitions)} total):")
        
        # For first 20 transitions, show state of all channels
        for i, (time, state) in enumerate(transitions[:20]):
            state_str = " ".join(f"CH{j}={state[j]}" for j in range(num_channels))
            print(f"  t={time:.6f}s  {state_str}")


def main():
    print("Loading data...")
    data = load_data(CAPTURE_PATH)
    print(f"Loaded {len(data)} samples\n")
    
    analyze_channel_behavior(data)
    analyze_correlations(data)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
