#!/usr/bin/env python3
"""
Debug the curved line path specifically
"""

import sys
sys.path.insert(0, 'src')

from core.paths import PathEngine

def debug_curve_path():
    engine = PathEngine()

    # Test the curved line path
    curve_path = "M50,100 Q150,50 250,100 T350,150"
    print("=== CURVE PATH DEBUG ===")
    print(f"Input: {curve_path}")

    result = engine.process_path(curve_path)
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
    debug_curve_path()