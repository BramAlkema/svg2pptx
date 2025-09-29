#!/usr/bin/env python3
"""
Debug the missing polygon and bezier paths
"""

import sys
sys.path.insert(0, 'src')

from src.paths import PathEngine

def debug_missing_paths():
    engine = PathEngine()

    print("=== POLYGON PATH DEBUG ===")
    polygon_path = "M300,200 L320,180 L340,185 L355,205 L345,225 L325,235 L305,230 L290,210 Z"
    print(f"Input: {polygon_path}")

    result = engine.process_path(polygon_path)
    path_data = result['path_data']

    print(f"Commands count: {path_data.command_count}")
    print(f"Commands structure: {path_data.commands}")

    for i in range(path_data.command_count):
        cmd = path_data.commands[i]
        print(f"Command {i}: type={cmd['type']}, relative={cmd['relative']}, coord_count={cmd['coord_count']}")
        if cmd['coord_count'] > 0:
            coords = cmd['coords'][:cmd['coord_count']]
            print(f"  Coordinates: {coords}")

    print("\n=== BEZIER PATH DEBUG ===")
    bezier_path = "M60,200 C60,180 80,180 100,200 S140,220 160,200"
    print(f"Input: {bezier_path}")

    result = engine.process_path(bezier_path)
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
    debug_missing_paths()