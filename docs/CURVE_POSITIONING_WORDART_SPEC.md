# Curve Positioning and WordArt Classification Specification

## Overview

This specification addresses the remaining flakiness in curve positioning and adds deterministic WordArt classification for native PowerPoint text warp presets. The goal is to make `sample_path_for_text()` deterministic and contract-true, while enabling automatic detection of common text path patterns that can be converted to native DrawingML WordArt.

## 1. Deterministic Path Sampling

### 1.1 Core Requirements

**Contract**: `sample_path_for_text(path_data, num_samples)` must:
- Always return exactly `num_samples` points (including both endpoints)
- Ensure strictly non-decreasing `distance_along_path` values
- Provide continuous tangent angles at segment joins
- Use equal arc-length sampling across the entire path

### 1.2 Implementation Strategy

#### A. Enhanced Command Parsing

**Current Support**: M, L, Q
**Required Additions**:

```python
# H, V → convert to L
def _expand_commands(cmd, params, current, start):
    """Expand multi-parameter commands and handle relative coordinates."""
    out = []
    it = iter(params)

    def abspt(x, y):
        return (current[0]+x, current[1]+y) if cmd.islower() else (x, y)

    if cmd.upper() == 'M':
        # First pair = moveto, remaining pairs are implicit L
        x, y = next(it, None), next(it, None)
        if x is None: return out, current, start
        x, y = abspt(x, y); current = (x, y); start = (x, y)
        prev = current
        for x, y in zip(it, it):  # Leftover pairs
            x, y = abspt(x, y)
            out.append(Line(prev, (x, y)))
            prev = (x, y)
        current = prev
    elif cmd.upper() == 'L':
        for x, y in zip(it, it):
            x, y = abspt(x, y)
            out.append(Line(current, (x, y)))
            current = (x, y)
    elif cmd.upper() == 'H':
        for x in it:
            x = current[0]+x if cmd.islower() else x
            out.append(Line(current, (x, current[1])))
            current = (x, current[1])
    elif cmd.upper() == 'V':
        for y in it:
            y = current[1]+y if cmd.islower() else y
            out.append(Line(current, (current[0], y)))
            current = (current[0], y)
    elif cmd.upper() == 'Z':
        if current != start:
            out.append(Line(current, start))
        current = start
    # ... Q, C expansions
    return out, current, start
```

#### B. Equal Arc-Length Sampling

Replace per-segment proportional sampling with global arc-length sampling:

```python
# Build segment list with cumulative lengths
segs = build_segments(commands)
cum = [0.0]
for s in segs:
    cum.append(cum[-1] + s.length())

N = num_samples or max(2, min(4096, ceil(cum[-1] * samples_per_unit)))
pts = []

for i in range(N):
    s_target = (cum[-1] * i) / (N-1) if N > 1 else 0
    # Binary search for segment
    j = bisect_right(cum, s_target) - 1
    j = min(max(j, 0), len(segs)-1)
    s_local = s_target - cum[j]
    t = segs[j].arclen_to_t(s_local)  # Invert with LUT or bisection
    x, y = segs[j].eval(t)
    tx, ty = segs[j].tan(t)
    angle = math.atan2(ty, tx)
    pts.append(PathPoint(
        x=x, y=y,
        tangent_angle=angle,
        distance_along_path=s_target
    ))
```

#### C. Segment Protocol

```python
class Segment:
    """Base class for path segments with arc-length operations."""

    def length(self) -> float:
        """Return total arc length of segment."""
        pass

    def eval(self, t: float) -> Tuple[float, float]:
        """Evaluate position at parameter t ∈ [0,1]."""
        pass

    def tan(self, t: float) -> Tuple[float, float]:
        """Evaluate tangent vector at parameter t."""
        pass

    def arclen_to_t(self, s: float) -> float:
        """Convert arc length s to parameter t via LUT/bisection."""
        pass

class Line(Segment):
    def __init__(self, p0, p1):
        self.p0, self.p1 = p0, p1
        self._length = math.sqrt((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2)

    def length(self): return self._length
    def eval(self, t): return (lerp(self.p0[0], self.p1[0], t), lerp(self.p0[1], self.p1[1], t))
    def tan(self, t): return normalize(self.p1[0]-self.p0[0], self.p1[1]-self.p0[1])
    def arclen_to_t(self, s): return s / self._length if self._length > 0 else 0

class Quadratic(Segment):
    def __init__(self, p0, p1, p2):
        self.p0, self.p1, self.p2 = p0, p1, p2
        self._build_arclen_lut()  # Precompute for fast inversion

    def eval(self, t):
        # Standard quadratic Bézier evaluation
        x = (1-t)**2 * self.p0[0] + 2*(1-t)*t * self.p1[0] + t**2 * self.p2[0]
        y = (1-t)**2 * self.p0[1] + 2*(1-t)*t * self.p1[1] + t**2 * self.p2[1]
        return (x, y)

    def tan(self, t):
        # Derivative: 2(1-t)(p1-p0) + 2t(p2-p1)
        dx = 2*(1-t)*(self.p1[0]-self.p0[0]) + 2*t*(self.p2[0]-self.p1[0])
        dy = 2*(1-t)*(self.p1[1]-self.p0[1]) + 2*t*(self.p2[1]-self.p1[1])
        return normalize(dx, dy)
```

### 1.3 Edge Case Handling

- **Zero-length segments**: Skip but preserve endpoint counts (dedupe coincident points)
- **Empty/malformed paths**: Return 2-point horizontal fallback
- **Multiple subpaths**: Use only referenced subpath; join with gap markers if needed

## 2. WordArt Classification System

### 2.1 Overview

Convert recognizable path patterns to native PowerPoint WordArt presets for better performance and native editing capabilities.

### 2.2 Classification Pipeline

```python
def classify_wordart(points):
    """
    Classify sampled path points for WordArt preset detection.

    Args:
        points: List of PathPoint with equal arc-length spacing

    Returns:
        (preset_name, parameters) or None if no match
    """
    # 1. Normalize and optimize orientation
    pts = normalize_and_best_rotate(points)
    if not is_x_monotone(pts):
        return None

    # 2. Test presets in priority order
    result = test_circle_arch(pts) or \
             test_inflate_deflate(pts) or \
             test_wave(pts) or \
             test_rise_slant(pts) or \
             test_triangle(pts)

    # 3. Validate with regeneration test
    if result and validate_regeneration(pts, result):
        return result
    return None
```

### 2.3 Preset Detection Algorithms

#### A. Circle/Arch Detection

```python
def test_circle_arch(pts):
    """Detect circular arcs and full circles."""
    circ = fit_circle_taubin(pts)
    rmse = rmse_circle(pts, circ)
    flip_count = curvature_flip_count(pts)

    if rmse < 0.02 and flip_count <= 2:
        if is_closed_path(pts):
            return ('circle', {'radius': circ.r})
        else:
            bend = calculate_bend_parameter(circ, span_x(pts))
            return ('arch', {'bend': bend})
    return None
```

#### B. Wave Detection

```python
def test_wave(pts):
    """Detect sinusoidal patterns via FFT analysis."""
    y_values = [p.y for p in pts]
    amplitude, frequency, snr = fit_sinusoid_fft(y_values)

    if snr > 8.0 and amplitude < 0.6:  # 8dB SNR threshold
        return ('wave', {
            'amplitude': amplitude,
            'period': 1.0 / frequency
        })
    return None
```

#### C. Inflate/Deflate Detection

```python
def test_inflate_deflate(pts):
    """Detect quadratic bowl shapes."""
    quad_fit = fit_quadratic_least_squares(pts)

    if quad_fit.r_squared > 0.98:
        preset = 'inflate' if quad_fit.a < 0 else 'deflate'
        return (preset, {'curvature': abs(quad_fit.a)})
    return None
```

### 2.4 DrawingML Generation

```python
def generate_wordart_drawingml(preset, params, text_props):
    """Generate WordArt DrawingML with preset and parameters."""

    preset_mappings = {
        'arch': 'textArchUp',
        'circle': 'textCircle',
        'wave': 'textWave1',
        'inflate': 'textInflate',
        'deflate': 'textDeflate',
        'rise': 'textSlantUp',
        'triangle': 'textTriangleUp'
    }

    prstTxWarp = ET.Element('a:prstTxWarp')
    prstTxWarp.set('prst', preset_mappings[preset])

    if params:
        avLst = ET.SubElement(prstTxWarp, 'a:avLst')

        param_mappings = {
            'bend': ('bend', lambda x: int(x * 100000)),  # Scale to DrawingML units
            'amplitude': ('adj', lambda x: int(x * 50000)),
            'period': ('adj2', lambda x: int(1.0/x * 100000)),
            'curvature': ('adj', lambda x: int(x * 25000))
        }

        for param_key, value in params.items():
            if param_key in param_mappings:
                gd_name, converter = param_mappings[param_key]
                gd = ET.SubElement(avLst, 'a:gd')
                gd.set('name', gd_name)
                gd.set('fmla', f'val {converter(value)}')

    return prstTxWarp
```

### 2.5 Quality Validation

```python
def validate_regeneration(original_pts, wordart_result):
    """Validate WordArt conversion quality."""
    preset, params = wordart_result

    # Regenerate baseline from WordArt parameters
    regenerated_pts = generate_wordart_baseline(preset, params, len(original_pts))

    # Compute normalized RMSE
    rmse_norm = compute_normalized_rmse(original_pts, regenerated_pts)

    # Check arc-length preservation
    max_arclength_error = compute_max_arclength_error(original_pts, regenerated_pts)

    return (rmse_norm <= 0.03 and
            max_arclength_error <= 0.02 and
            not has_self_overlap(regenerated_pts))
```

## 3. Implementation Plan

### 3.1 Phase 1: Deterministic Sampling
1. Update `curve_text_positioning.py` with new segment protocol
2. Implement equal arc-length sampling algorithm
3. Add comprehensive command parsing (H, V, Z, relative commands)
4. Create regression tests for determinism

### 3.2 Phase 2: WordArt Classification
1. Implement normalization and rotation optimization
2. Add preset detection algorithms (circle, wave, inflate, etc.)
3. Create DrawingML generation for WordArt presets
4. Add quality validation and fallback logic

### 3.3 Phase 3: Integration
1. Wire WordArt classifier into text processing pipeline
2. Add configuration for WordArt detection thresholds
3. Implement performance optimizations (early exit heuristics)
4. Create comprehensive test suite

## 4. Testing Requirements

### 4.1 Determinism Tests
```python
def test_exact_sample_count():
    """Verify exact point count for all inputs."""
    for N in [2, 10, 31, 257]:
        points = sample_path_for_text("M0,0 L100,0 Q150,50 200,0", N)
        assert len(points) == N

def test_monotonic_distance():
    """Verify strictly increasing distance_along_path."""
    points = sample_path_for_text("M0,0 L100,0 L100,100", 50)
    distances = [p.distance_along_path for p in points]
    assert all(distances[i] <= distances[i+1] for i in range(len(distances)-1))
```

### 4.2 WordArt Classification Tests
```python
def test_circle_detection():
    """Verify circle preset detection."""
    # Perfect circle path
    circle_path = generate_circle_path(radius=50, center=(0,0))
    points = sample_path_for_text(circle_path, 128)
    result = classify_wordart(points)
    assert result[0] == 'circle'
    assert abs(result[1]['radius'] - 50) < 1.0

def test_wave_detection():
    """Verify wave preset detection."""
    # Sinusoidal path
    wave_path = generate_wave_path(amplitude=20, frequency=2, length=200)
    points = sample_path_for_text(wave_path, 128)
    result = classify_wordart(points)
    assert result[0] == 'wave'
```

## 5. Performance Targets

- **Sampling**: <5ms for paths with <100 segments
- **Classification**: <10ms for 128-point analysis
- **Memory**: <1MB working set for typical text paths
- **Accuracy**: >95% correct classification for synthetic test cases

## 6. Configuration

```python
WORDART_CONFIG = {
    'enable_classification': True,
    'sample_count_range': (64, 256),
    'classification_thresholds': {
        'circle_rmse': 0.02,
        'wave_snr_db': 8.0,
        'quadratic_r2': 0.98,
        'linear_r2': 0.995
    },
    'validation_thresholds': {
        'regeneration_rmse': 0.03,
        'arclength_error': 0.02
    }
}
```

This specification provides a complete roadmap for eliminating curve positioning flakiness and adding robust WordArt classification to the text processing pipeline.