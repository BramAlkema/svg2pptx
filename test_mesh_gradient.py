#!/usr/bin/env python3
"""
Test mesh gradients through the pipeline.
SVG 2.0 mesh gradients are complex multi-patch color interpolation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.batch.tasks import convert_single_svg

# SVG 2.0 Mesh Gradient
mesh_gradient_svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="400" height="400" viewBox="0 0 400 400">
  <defs>
    <!-- Simple 2x2 mesh gradient -->
    <meshgradient id="meshGrad1" x="0" y="0">
      <meshrow>
        <meshpatch>
          <stop path="c 25,0  25,25  0,25" stop-color="#ff0000"/>
          <stop path="c 0,25  -25,25  -25,0" stop-color="#00ff00"/>
          <stop path="c -25,0  -25,-25  0,-25" stop-color="#0000ff"/>
          <stop path="c 0,-25  25,-25  25,0" stop-color="#ffff00"/>
        </meshpatch>
        <meshpatch>
          <stop path="c 25,0  25,25  0,25" stop-color="#00ff00"/>
          <stop path="c 0,25  -25,25  -25,0" stop-color="#ff00ff"/>
          <stop path="c -25,0  -25,-25  0,-25" stop-color="#00ffff"/>
          <stop path="c 0,-25  25,-25  25,0" stop-color="#ffffff"/>
        </meshpatch>
      </meshrow>
      <meshrow>
        <meshpatch>
          <stop path="c 25,0  25,25  0,25" stop-color="#0000ff"/>
          <stop path="c 0,25  -25,25  -25,0" stop-color="#ffff00"/>
          <stop path="c -25,0  -25,-25  0,-25" stop-color="#ff00ff"/>
          <stop path="c 0,-25  25,-25  25,0" stop-color="#00ff00"/>
        </meshpatch>
        <meshpatch>
          <stop path="c 25,0  25,25  0,25" stop-color="#ffff00"/>
          <stop path="c 0,25  -25,25  -25,0" stop-color="#00ffff"/>
          <stop path="c -25,0  -25,-25  0,-25" stop-color="#ff0000"/>
          <stop path="c 0,-25  25,-25  25,0" stop-color="#ffffff"/>
        </meshpatch>
      </meshrow>
    </meshgradient>

    <!-- Coons patch mesh (simpler) -->
    <meshgradient id="meshGrad2" type="coons">
      <meshrow>
        <meshpatch>
          <stop path="c 100,0 100,0 100,0" stop-color="red"/>
          <stop path="c 0,100 0,100 0,100" stop-color="green"/>
          <stop path="c -100,0 -100,0 -100,0" stop-color="blue"/>
          <stop path="c 0,-100 0,-100 0,-100" stop-color="yellow"/>
        </meshpatch>
      </meshrow>
    </meshgradient>

    <!-- Complex mesh with opacity -->
    <meshgradient id="meshGrad3" x="50" y="50">
      <meshrow>
        <meshpatch>
          <stop path="c 50,0 50,50 0,50" stop-color="rgba(255,0,0,1)"/>
          <stop path="c 0,50 -50,50 -50,0" stop-color="rgba(0,255,0,0.5)"/>
          <stop path="c -50,0 -50,-50 0,-50" stop-color="rgba(0,0,255,0.8)"/>
          <stop path="c 0,-50 50,-50 50,0" stop-color="rgba(255,255,0,0.3)"/>
        </meshpatch>
      </meshrow>
    </meshgradient>
  </defs>

  <!-- Test 1: Rectangle with 2x2 mesh -->
  <rect x="10" y="10" width="180" height="180" fill="url(#meshGrad1)"/>
  <text x="100" y="210" font-size="12" text-anchor="middle">2x2 Mesh</text>

  <!-- Test 2: Circle with Coons patch -->
  <circle cx="300" cy="100" r="90" fill="url(#meshGrad2)"/>
  <text x="300" y="210" font-size="12" text-anchor="middle">Coons Patch</text>

  <!-- Test 3: Ellipse with opacity mesh -->
  <ellipse cx="200" cy="300" rx="120" ry="80" fill="url(#meshGrad3)"/>
  <text x="200" y="390" font-size="12" text-anchor="middle">Opacity Mesh</text>

  <!-- Test 4: Path with mesh -->
  <path d="M 50,250 Q 100,220 150,250 T 250,250 L 250,320 L 50,320 Z"
        fill="url(#meshGrad1)"
        stroke="black"
        stroke-width="2"/>
</svg>'''

# Fallback test: What happens with mesh gradients
fallback_test = '''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">
  <defs>
    <!-- This should trigger fallback behavior -->
    <meshgradient id="mesh">
      <meshrow>
        <meshpatch>
          <stop path="c 50,0 50,50 0,50" stop-color="red"/>
          <stop path="c 0,50 -50,50 -50,0" stop-color="blue"/>
          <stop path="c -50,0 -50,-50 0,-50" stop-color="green"/>
          <stop path="c 0,-50 50,-50 50,0" stop-color="yellow"/>
        </meshpatch>
      </meshrow>
    </meshgradient>
  </defs>

  <!-- Should convert mesh to simpler gradient or solid color -->
  <rect x="50" y="50" width="200" height="200" fill="url(#mesh)" stroke="black" stroke-width="2"/>
  <text x="150" y="270" font-size="14" text-anchor="middle">Mesh Gradient Fallback Test</text>
</svg>'''

def test_mesh_gradients():
    """Test mesh gradient support"""

    print("🎨 Testing Mesh Gradients")
    print("=" * 70)

    # Job 1: Complex mesh
    print("\n📊 Job 1: SVG 2.0 mesh gradients (2x2, Coons, opacity)")
    file_data_1 = {
        'filename': 'mesh_complex.svg',
        'content': mesh_gradient_svg.encode('utf-8'),
        'metadata': {'test': 'mesh_gradient', 'complexity': 'high'}
    }

    result_1 = convert_single_svg(file_data_1, {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    })

    print(f"   ✅ Queued: {result_1.id if hasattr(result_1, 'id') else 'N/A'}")

    # Job 2: Fallback test
    print("\n📊 Job 2: Mesh gradient fallback behavior")
    file_data_2 = {
        'filename': 'mesh_fallback.svg',
        'content': fallback_test.encode('utf-8'),
        'metadata': {'test': 'mesh_fallback'}
    }

    result_2 = convert_single_svg(file_data_2, {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    })

    print(f"   ✅ Queued: {result_2.id if hasattr(result_2, 'id') else 'N/A'}")

    # Wait for results
    print("\n⏳ Waiting for jobs...")
    import time

    jobs = [('Mesh Complex', result_1), ('Mesh Fallback', result_2)]
    results = []

    max_wait = 30
    start_time = time.time()

    while time.time() - start_time < max_wait:
        all_done = True

        for name, result in jobs:
            if result not in [r[1] for r in results]:
                if result() is not None:
                    job_result = result()
                    results.append((name, result))

                    print(f"\n✅ {name} completed!")
                    print(f"   Status: {job_result.get('status', 'unknown')}")

                    if 'error' in job_result:
                        print(f"   ❌ Error: {job_result['error']}")
                    elif 'output_path' in job_result:
                        output_path = job_result['output_path']
                        print(f"   📁 Output: {output_path}")

                        # Check file
                        output_file = Path(output_path)
                        if output_file.exists():
                            size_kb = output_file.stat().st_size / 1024
                            print(f"   📦 Size: {size_kb:.1f} KB")

                    if 'conversion_time' in job_result:
                        print(f"   ⏱️  Time: {job_result['conversion_time']:.3f}s")
                else:
                    all_done = False

        if all_done:
            break

        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("📊 MESH GRADIENT TEST SUMMARY")
    print("=" * 70)
    print(f"Jobs completed: {len(results)}/{len(jobs)}")

    if len(results) == len(jobs):
        print("✅ Mesh gradient processing complete!")
        print("\n💡 NOTE: Mesh gradients may fall back to:")
        print("   - Linear/radial gradient approximation")
        print("   - Average solid color")
        print("   - Transparent/no fill")
        return True
    else:
        print(f"⚠️  {len(jobs) - len(results)} jobs failed")
        return False

if __name__ == "__main__":
    success = test_mesh_gradients()
    sys.exit(0 if success else 1)
