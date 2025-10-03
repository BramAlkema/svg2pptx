#!/usr/bin/env python3
"""
Test Huey job queue with W3C-level complexity:
- Stacked filter effects
- Complex gradients and patterns
- Nested groups with transforms
- Clipping and masking
- Text with tspan and textPath
- All path commands (Q, T, H, V, C, S, A)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.batch.tasks import convert_single_svg

# W3C-level complex SVG with stacked filters
w3c_complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="800" height="600" viewBox="0 0 800 600">
  <defs>
    <!-- Complex gradient with multiple stops -->
    <linearGradient id="complexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
      <stop offset="33%" style="stop-color:rgb(0,255,0);stop-opacity:0.8" />
      <stop offset="66%" style="stop-color:rgb(0,0,255);stop-opacity:0.6" />
      <stop offset="100%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
    </linearGradient>

    <!-- Radial gradient -->
    <radialGradient id="radialGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:white;stop-opacity:1" />
      <stop offset="100%" style="stop-color:purple;stop-opacity:1" />
    </radialGradient>

    <!-- Pattern -->
    <pattern id="checkerboard" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect x="0" y="0" width="20" height="20" fill="black"/>
      <rect x="20" y="20" width="20" height="20" fill="black"/>
      <rect x="20" y="0" width="20" height="20" fill="white"/>
      <rect x="0" y="20" width="20" height="20" fill="white"/>
    </pattern>

    <!-- Stacked filter effects -->
    <filter id="stackedFilters" x="-50%" y="-50%" width="200%" height="200%">
      <!-- Gaussian blur -->
      <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>

      <!-- Offset -->
      <feOffset in="blur" dx="3" dy="3" result="offsetBlur"/>

      <!-- Color matrix (desaturate) -->
      <feColorMatrix in="offsetBlur" type="saturate" values="0.3" result="desaturated"/>

      <!-- Composite -->
      <feComposite in="SourceGraphic" in2="desaturated" operator="over" result="composite"/>

      <!-- Blend -->
      <feBlend in="composite" in2="SourceGraphic" mode="multiply"/>
    </filter>

    <!-- Lighting filter -->
    <filter id="lighting" x="0%" y="0%" width="100%" height="100%">
      <feSpecularLighting in="SourceGraphic" surfaceScale="5" specularConstant="0.75"
                          specularExponent="20" lighting-color="white" result="specOut">
        <fePointLight x="100" y="100" z="200"/>
      </feSpecularLighting>
      <feComposite in="SourceGraphic" in2="specOut" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
    </filter>

    <!-- Clipping path with complex shape -->
    <clipPath id="complexClip">
      <path d="M 50,50 Q 100,25 150,50 T 250,50 L 250,150 C 250,200 200,250 150,250 S 50,200 50,150 Z"/>
    </clipPath>

    <!-- Mask -->
    <mask id="fadeMask">
      <rect x="0" y="0" width="800" height="600" fill="url(#radialGrad)"/>
    </mask>

    <!-- Path for textPath -->
    <path id="textCurve" d="M 100,300 Q 250,200 400,300 T 700,300" fill="none" stroke="gray" stroke-width="1"/>
  </defs>

  <!-- Background with pattern -->
  <rect x="0" y="0" width="800" height="600" fill="url(#checkerboard)" opacity="0.1"/>

  <!-- Group with nested transforms -->
  <g transform="translate(100,50) rotate(5) scale(1.1)">
    <!-- Rectangle with gradient and filter -->
    <rect x="0" y="0" width="200" height="150" fill="url(#complexGrad)"
          filter="url(#stackedFilters)" rx="10" ry="10"/>

    <!-- Nested group with clipping -->
    <g clip-path="url(#complexClip)">
      <circle cx="100" cy="100" r="80" fill="orange" opacity="0.7"/>
      <ellipse cx="150" cy="100" rx="60" ry="40" fill="cyan" opacity="0.6"/>
    </g>
  </g>

  <!-- Path with all command types -->
  <path d="M 300,100
           L 350,100
           H 400
           V 150
           Q 450,175 500,150
           T 600,150
           C 650,100 700,200 750,150
           S 750,50 700,50
           A 50,50 0 0,1 650,100
           Z"
        fill="url(#radialGrad)"
        stroke="black"
        stroke-width="2"
        filter="url(#lighting)"/>

  <!-- Polygon with mask -->
  <polygon points="50,400 100,350 150,400 125,450 75,450"
           fill="red"
           mask="url(#fadeMask)"/>

  <!-- Polyline -->
  <polyline points="200,400 250,350 300,380 350,340 400,390"
            fill="none"
            stroke="blue"
            stroke-width="3"/>

  <!-- Line -->
  <line x1="450" y1="350" x2="550" y2="450"
        stroke="green"
        stroke-width="5"
        stroke-dasharray="10,5"/>

  <!-- Text with multiple runs and styling -->
  <text x="50" y="500" font-family="Arial" font-size="24">
    <tspan fill="red" font-weight="bold">Complex</tspan>
    <tspan fill="blue" font-style="italic" dx="5">SVG</tspan>
    <tspan fill="green" text-decoration="underline" dx="5">Test</tspan>
  </text>

  <!-- Text on path -->
  <text font-family="Arial" font-size="18" fill="purple">
    <textPath xlink:href="#textCurve" startOffset="10%">
      Text following a curved path with Q and T commands
    </textPath>
  </text>

  <!-- Image reference (placeholder) -->
  <image x="600" y="400" width="150" height="150"
         xlink:href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100' height='100' fill='orange'/%3E%3C/svg%3E"/>

  <!-- Use/symbol pattern -->
  <symbol id="star" viewBox="0 0 100 100">
    <polygon points="50,10 61,40 95,40 67,60 79,90 50,70 21,90 33,60 5,40 39,40"/>
  </symbol>

  <use xlink:href="#star" x="50" y="50" width="50" height="50" fill="gold"/>
  <use xlink:href="#star" x="650" y="50" width="40" height="40" fill="silver" transform="rotate(15 670 70)"/>
</svg>'''

def test_push_complex_jobs():
    """Push multiple W3C-level complex jobs to queue"""

    print("🚀 Testing Huey Queue with W3C Complexity")
    print("=" * 70)

    jobs = []

    # Job 1: Full W3C complexity
    print("\n📊 Job 1: Full W3C complexity (stacked filters, all elements)")
    file_data_1 = {
        'filename': 'w3c_complex.svg',
        'content': w3c_complex_svg.encode('utf-8'),
        'metadata': {'test': 'w3c_full', 'complexity': 'maximum'}
    }

    result_1 = convert_single_svg(file_data_1, {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    })
    jobs.append(('W3C Full', result_1))
    print(f"   ✅ Queued: {result_1.id if hasattr(result_1, 'id') else 'N/A'}")

    # Job 2: Filter stress test
    filter_stress = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
      <defs>
        <filter id="multiFilter" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
          <feColorMatrix in="blur" type="matrix"
                        values="0.33 0.33 0.33 0 0
                                0.33 0.33 0.33 0 0
                                0.33 0.33 0.33 0 0
                                0 0 0 1 0" result="grayscale"/>
          <feComponentTransfer in="grayscale" result="contrast">
            <feFuncR type="linear" slope="2" intercept="-0.5"/>
            <feFuncG type="linear" slope="2" intercept="-0.5"/>
            <feFuncB type="linear" slope="2" intercept="-0.5"/>
          </feComponentTransfer>
          <feOffset in="contrast" dx="5" dy="5" result="offset"/>
          <feBlend in="SourceGraphic" in2="offset" mode="multiply"/>
        </filter>
      </defs>
      <rect x="50" y="50" width="300" height="300" fill="blue" filter="url(#multiFilter)"/>
      <circle cx="200" cy="200" r="80" fill="red" filter="url(#multiFilter)"/>
    </svg>'''

    print("\n📊 Job 2: Filter stress test (5-stage filter chain)")
    file_data_2 = {
        'filename': 'filter_stress.svg',
        'content': filter_stress.encode('utf-8'),
        'metadata': {'test': 'filter_stress', 'filters': 5}
    }

    result_2 = convert_single_svg(file_data_2, {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    })
    jobs.append(('Filter Stress', result_2))
    print(f"   ✅ Queued: {result_2.id if hasattr(result_2, 'id') else 'N/A'}")

    # Job 3: Path command exhaustive
    path_exhaustive = '''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">
      <!-- M, L commands -->
      <path d="M 50,50 L 100,50 L 100,100 L 50,100 Z" fill="red"/>

      <!-- H, V commands -->
      <path d="M 150,50 H 200 V 100 H 150 Z" fill="blue"/>

      <!-- Q (quadratic) command -->
      <path d="M 250,50 Q 300,25 350,50 L 350,100 L 250,100 Z" fill="green"/>

      <!-- T (smooth quadratic) command -->
      <path d="M 400,50 Q 425,25 450,50 T 500,50 L 500,100 L 400,100 Z" fill="orange"/>

      <!-- C (cubic) command -->
      <path d="M 50,150 C 75,125 125,125 150,150 L 150,200 L 50,200 Z" fill="purple"/>

      <!-- S (smooth cubic) command -->
      <path d="M 200,150 C 225,125 275,125 300,150 S 350,200 350,200 L 200,200 Z" fill="cyan"/>

      <!-- A (arc) command -->
      <path d="M 400,150 A 50,50 0 0,1 500,150 L 500,200 L 400,200 Z" fill="magenta"/>

      <!-- All combined -->
      <path d="M 50,250 L 100,250 H 150 V 300 Q 200,275 250,300 T 350,300
               C 400,250 450,350 500,300 S 550,250 550,250
               A 25,25 0 1,0 550,350 L 50,350 Z"
            fill="yellow" stroke="black" stroke-width="2"/>
    </svg>'''

    print("\n📊 Job 3: Path command exhaustive (M, L, H, V, Q, T, C, S, A)")
    file_data_3 = {
        'filename': 'path_exhaustive.svg',
        'content': path_exhaustive.encode('utf-8'),
        'metadata': {'test': 'path_commands', 'commands': 'all'}
    }

    result_3 = convert_single_svg(file_data_3, {
        'slide_width': 10.0,
        'slide_height': 7.5,
        'quality': 'high'
    })
    jobs.append(('Path Commands', result_3))
    print(f"   ✅ Queued: {result_3.id if hasattr(result_3, 'id') else 'N/A'}")

    # Wait for all jobs
    print("\n⏳ Waiting for jobs to complete...")
    print("=" * 70)

    max_wait = 60
    start_time = time.time()
    results = []

    while time.time() - start_time < max_wait:
        all_done = True

        for name, result in jobs:
            if result not in [r[1] for r in results]:
                if result() is not None:
                    job_result = result()
                    results.append((name, result))

                    print(f"\n✅ {name} completed!")
                    print(f"   Status: {job_result.get('status', 'unknown')}")
                    print(f"   Filename: {job_result.get('filename', 'N/A')}")

                    if 'error' in job_result:
                        print(f"   ❌ Error: {job_result['error']}")
                    elif 'output_path' in job_result:
                        output_path = job_result['output_path']
                        print(f"   📁 Output: {output_path}")

                        # Check file size
                        output_file = Path(output_path)
                        if output_file.exists():
                            size_kb = output_file.stat().st_size / 1024
                            print(f"   📦 Size: {size_kb:.1f} KB")

                    if 'conversion_time' in job_result:
                        print(f"   ⏱️  Time: {job_result['conversion_time']:.2f}s")

                    if 'elements_processed' in job_result:
                        print(f"   🔢 Elements: {job_result['elements_processed']}")
                else:
                    all_done = False

        if all_done:
            break

        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Jobs completed: {len(results)}/{len(jobs)}")

    if len(results) == len(jobs):
        print("✅ All jobs completed successfully!")
        return True
    else:
        print(f"⚠️  {len(jobs) - len(results)} jobs still pending/failed")
        print("\n💡 TIP: Start Huey worker in another terminal:")
        print("   ./start_huey_worker.sh")
        return False

if __name__ == "__main__":
    success = test_push_complex_jobs()
    sys.exit(0 if success else 1)
