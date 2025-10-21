#!/usr/bin/env python3
"""Enhanced tooling to inspect Saleae CSV dumps for LCD reverse engineering.

Usage:
    python analysis/analyze_signals.py

The script analyzes:
- Channel activity and transitions
- Timing patterns and pulse widths
- Potential protocol detection (SPI, parallel, custom)
- Data extraction based on identified protocol
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, Iterable, List, Tuple, Optional

CAPTURE_PATH = Path(__file__).resolve().parent.parent / "digital.csv"

# Initial channel naming - will be refined based on analysis
CHANNEL_NAMES = {
    0: "CH0",
    1: "CH1_TRIGGER",  # This is the trigger/reset/enable
    2: "CH2",
    3: "CH3",
    4: "CH4",
}


@dataclass
class Edge:
    time: float
    channel: int
    from_state: int
    to_state: int


def iter_rows(path: Path) -> Iterable[Tuple[float, Tuple[int, ...]]]:
    """Yield timestamp and channel states."""
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if not header or header[0].strip().lower() != "time [s]":
            raise ValueError("Unexpected header: {header!r}")
        for row in reader:
            if not row:
                continue
            time = float(row[0])
            states = tuple(int(bit) for bit in row[1:])
            yield time, states


def collect_edges(rows: Iterable[Tuple[float, Tuple[int, ...]]]) -> Tuple[List[Edge], Dict[int, List[float]], List[Tuple[float, Tuple[int, ...]]]]:
    """Collect edge events and store state history for later passes."""
    edges: List[Edge] = []
    deltas: Dict[int, List[float]] = defaultdict(list)
    history: List[Tuple[float, Tuple[int, ...]]] = []
    prev_time = None
    prev_state = None

    for time, state in rows:
        history.append((time, state))
        if prev_state is None:
            prev_time = time
            prev_state = state
            continue

        dt = time - prev_time
        if dt < 0:
            # Saleae exports sometimes include negative offsets before zero; ignore for delta stats.
            dt = None

        for channel, (old_bit, new_bit) in enumerate(zip(prev_state, state)):
            if old_bit != new_bit:
                edges.append(Edge(time=time, channel=channel, from_state=old_bit, to_state=new_bit))
                if dt is not None:
                    deltas[channel].append(dt)

        prev_time = time
        prev_state = state

    return edges, deltas, history


def summarize_deltas(deltas: Dict[int, List[float]]) -> str:
    lines = []
    for channel in sorted(deltas):
        values = deltas[channel]
        if not values:
            continue
        lines.append(
            f"  {CHANNEL_NAMES.get(channel, channel)}: count={len(values):6d}  median={median(values):.3e}s  mean={mean(values):.3e}s"
        )
    return "\n".join(lines)


def summarize_edges(edges: List[Edge]) -> str:
    counter = Counter((edge.channel, edge.from_state, edge.to_state) for edge in edges)
    lines = []
    for (channel, frm, to), count in sorted(counter.items()):
        lines.append(f"  {CHANNEL_NAMES.get(channel, channel)} {frm}->{to}: {count}")
    return "\n".join(lines)


def summarize_capture(history: List[Tuple[float, Tuple[int, ...]]]) -> str:
    if not history:
        return "(empty)"
    start_time = history[0][0]
    end_time = history[-1][0]
    duration = end_time - start_time
    samples = len(history)
    return f"Samples: {samples}  start={start_time:.6f}s  end={end_time:.6f}s  duration={duration:.6f}s"


def find_spi_frames(history: List[Tuple[float, Tuple[int, ...]]]) -> List[Dict[str, object]]:
    """Split the timeline into CS-low frames and extract coarse metadata."""
    frames: List[Dict[str, object]] = []
    if len(history) < 2:
        return frames

    current: Dict[str, object] | None = None
    last_clk_rise = None

    prev_time, prev_state = history[0]
    for time, state in history[1:]:
        prev_cs, prev_clk, prev_dc, prev_mosi, *_ = prev_state
        cs, clk, d_c, mosi, *_ = state

        if prev_cs == 1 and cs == 0:
            current = {
                "start": time,
                "edge_count": 0,
                "d_c": d_c,
                "periods": [],
                "bits": [],
            }
            last_clk_rise = None
        elif prev_cs == 0 and cs == 1 and current is not None:
            current["end"] = time
            frames.append(current)
            current = None
            last_clk_rise = None

        if current is not None:
            # Rising edge on clock defines a data capture moment (mode 0 assumption).
            if prev_clk == 0 and clk == 1:
                if last_clk_rise is not None:
                    current["periods"].append(time - last_clk_rise)
                current["bits"].append(prev_mosi)
                current["edge_count"] += 1
                last_clk_rise = time

        prev_time, prev_state = time, state

    # Handle dangling frame if CS never returned high.
    if current is not None and "end" not in current:
        current["end"] = history[-1][0]
        frames.append(current)

    return frames


def analyze_pulse_widths(history: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Analyze pulse widths for each channel to understand timing patterns."""
    print("== Pulse Width Analysis ==")
    
    for channel in range(5):
        high_pulses = []
        low_pulses = []
        
        in_high = None
        in_low = None
        
        for time, state in history:
            if time < 0:  # Skip pre-trigger
                continue
                
            bit = state[channel] if channel < len(state) else 0
            
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
            print(f"\n{CHANNEL_NAMES.get(channel, f'CH{channel}')} HIGH pulses:")
            print(f"  Count: {len(high_pulses)}")
            print(f"  Min: {min(high_pulses)*1e6:.2f} µs")
            print(f"  Max: {max(high_pulses)*1e6:.2f} µs")
            print(f"  Mean: {mean(high_pulses)*1e6:.2f} µs")
            print(f"  Median: {median(high_pulses)*1e6:.2f} µs")
            if len(high_pulses) > 1:
                print(f"  StdDev: {stdev(high_pulses)*1e6:.2f} µs")
        
        if low_pulses and len(low_pulses) > 1:
            print(f"\n{CHANNEL_NAMES.get(channel, f'CH{channel}')} LOW pulses:")
            print(f"  Count: {len(low_pulses)}")
            print(f"  Min: {min(low_pulses)*1e6:.2f} µs")
            print(f"  Max: {max(low_pulses)*1e6:.2f} µs")
            print(f"  Mean: {mean(low_pulses)*1e6:.2f} µs")
            print(f"  Median: {median(low_pulses)*1e6:.2f} µs")


def analyze_parallel_protocol(history: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Analyze if this is a parallel bus protocol with clock/strobe."""
    print("\n== Parallel Protocol Analysis ==")
    
    # Look for a clock or strobe signal (frequent transitions)
    post_trigger = [(t, s) for t, s in history if t >= 0]
    
    if not post_trigger:
        print("No post-trigger data!")
        return
    
    # Analyze CH0 as potential strobe/enable
    print("\nAnalyzing CH0 as strobe/enable signal:")
    ch0_transitions = []
    prev_ch0 = None
    
    for time, state in post_trigger:
        ch0 = state[0] if len(state) > 0 else 0
        if prev_ch0 is not None and ch0 != prev_ch0:
            ch0_transitions.append((time, prev_ch0, ch0))
        prev_ch0 = ch0
    
    print(f"  Total transitions: {len(ch0_transitions)}")
    
    # On rising edges of CH0, capture other channels
    print("\nData on CH0 rising edges (first 50):")
    count = 0
    for time, state in post_trigger:
        if count >= 50:
            break
        ch0 = state[0] if len(state) > 0 else 0
        if ch0 == 1:  # Look at state during high
            ch2 = state[2] if len(state) > 2 else 0
            ch3 = state[3] if len(state) > 3 else 0
            ch4 = state[4] if len(state) > 4 else 0
            print(f"  t={time:.6f}s  CH2={ch2} CH3={ch3} CH4={ch4}")
            count += 1


def decode_data_stream(history: List[Tuple[float, Tuple[int, ...]]]) -> None:
    """Attempt to decode data based on edge patterns."""
    print("\n== Data Stream Decoding ==")
    
    # Focus on post-trigger data
    post_trigger = [(t, s) for t, s in history if t >= 0]
    
    # Look for data transitions on CH3 and CH4
    print("\nCH3 transitions (first 100):")
    prev_state = None
    count = 0
    
    for time, state in post_trigger:
        if count >= 100:
            break
        ch3 = state[3] if len(state) > 3 else 0
        
        if prev_state is not None and ch3 != prev_state:
            ch0 = state[0] if len(state) > 0 else 0
            ch2 = state[2] if len(state) > 2 else 0
            print(f"  t={time:.6f}s  {prev_state}->{ch3}  (CH0={ch0}, CH2={ch2})")
            count += 1
        
        prev_state = ch3


def main() -> None:
    rows = list(iter_rows(CAPTURE_PATH))
    edges, deltas, history = collect_edges(rows)

    print("== Capture summary ==")
    print(summarize_capture(history))
    print()

    print("== Edge counts ==")
    print(summarize_edges(edges))
    print()

    print("== Delta stats (raw adjacency between Saleae events) ==")
    print(summarize_deltas(deltas))
    print()
    
    # New analysis functions
    analyze_pulse_widths(history)
    analyze_parallel_protocol(history)
    decode_data_stream(history)
    
    # Keep original SPI analysis as reference
    print("\n" + "="*60)
    print("== Original SPI Analysis (for reference) ==")
    frames = find_spi_frames(history)
    if frames:
        print(f"\nFound {len(frames)} CS-low frames")
        for idx, frame in enumerate(frames[:5]):
            periods = frame.get("periods", [])
            bits = frame.get("bits", [])
            avg_period = median(periods) if periods else float("nan")
            freq = (1.0 / avg_period) if avg_period and avg_period > 0 else float("nan")
            print(
                f"Frame {idx:03d}: start={frame['start']:.6f}s  end={frame.get('end', frame['start']):.6f}s  "
                f"D/C={frame['d_c']}  edges={frame['edge_count']}"
            )


if __name__ == "__main__":
    main()
