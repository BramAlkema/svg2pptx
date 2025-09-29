#!/usr/bin/env python3
"""
Debug the PathEngine output to see what command structure is actually generated
"""

import sys
sys.path.insert(0, 'src')

from core.paths import PathEngine

def debug_path_engine():
    engine = PathEngine()

    # Test the star path (working)
    star_path = "M100,50 L105,65 L120,65 L108,75 L113,90 L100,80 L87,90 L92,75 L80,65 L95,65 Z"
    print("=== STAR PATH DEBUG ===")
    print(f"Input: {star_path}")

    result = engine.process_path(star_path)
    path_data = result['path_data']

    print(f"Commands count: {path_data.command_count}")
    print(f"Commands structure: {path_data.commands}")

    for i in range(path_data.command_count):
        cmd = path_data.commands[i]
        print(f"Command {i}: type={cmd['type']}, relative={cmd['relative']}, coord_count={cmd['coord_count']}")
        if cmd['coord_count'] > 0:
            coords = cmd['coords'][:cmd['coord_count']]
            print(f"  Coordinates: {coords}")

    print("\n=== HEART PATH DEBUG ===")
    # Test the heart path (broken)
    heart_path = "M200,220 C200,220 150,170 120,140 C90,110 90,70 120,70 C140,70 160,80 200,120 C240,80 260,70 280,70 C310,70 310,110 280,140 C250,170 200,220 200,220 Z"
    print(f"Input: {heart_path}")

    result = engine.process_path(heart_path)
    path_data = result['path_data']

    print(f"Commands count: {path_data.command_count}")
    print(f"Commands structure: {path_data.commands}")

    for i in range(path_data.command_count):
        cmd = path_data.commands[i]
        print(f"Command {i}: type={cmd['type']}, relative={cmd['relative']}, coord_count={cmd['coord_count']}")
        if cmd['coord_count'] > 0:
            coords = cmd['coords'][:cmd['coord_count']]
            print(f"  Coordinates: {coords}")

if __name__ == "__main__":
    debug_path_engine()