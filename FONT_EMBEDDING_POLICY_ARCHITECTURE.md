# Font Embedding Policy Architecture

**Status**: ✅ REFACTORED - Policy-Driven Design
**Date**: 2025-10-02

---

## Overview

Font embedding decisions are now **policy-driven**, moving deduplication and configuration logic from the coordinator into the PolicyEngine. This ensures consistency with the rest of the codebase and provides centralized, configurable control.

---

## Architecture Decision

### Before (Hardcoded Logic)

```python
# ❌ Coordinator had embedded business logic
class SVGFontEmbedCoordinator:
    def harvest_and_embed(...):
        faces = extract_embedded_faces(svg_string)
        faces = [f for f in faces if f.sha1 not in self._seen_sha]  # Hardcoded dedup
        # No size limits, no configuration
```

### After (Policy-Driven)

```python
# ✅ Policy engine makes decisions
class PolicyEngine:
    def decide_font_embedding(self, font_family, font_size_bytes,
                             sha1_checksum, already_embedded) -> FontEmbeddingDecision:
        # Check deduplication
        if sha1_checksum in already_embedded:
            return FontEmbeddingDecision.skip(reasons=[FONT_ALREADY_EMBEDDED])

        # Check configuration
        if not self.config.enable_font_embedding:
            return FontEmbeddingDecision.skip(reasons=[EMBEDDING_DISABLED])

        # Check size limits
        if font_size_bytes > max_size:
            return FontEmbeddingDecision.skip(reasons=[FONT_SIZE_LIMIT_EXCEEDED])

        # Embed
        return FontEmbeddingDecision.embed(reasons=[CUSTOM_FONT_REQUIRED])
```

---

## Components

### 1. PolicyEngine (Decision Maker)

**File**: `core/policy/engine.py:879`

**Method**: `decide_font_embedding(font_family, font_size_bytes, sha1_checksum, already_embedded)`

**Decisions**:
- ✅ **EMBED**: Custom font required
- ❌ **SKIP**: Already embedded (deduplication)
- ❌ **SKIP**: Embedding disabled (configuration)
- ❌ **SKIP**: Size limit exceeded (10MB default)

**Returns**: `FontEmbeddingDecision` with:
- `should_embed: bool` - Whether to embed the font
- `reasons: List[DecisionReason]` - Why this decision was made
- `font_family: str` - Font family name
- `font_size_bytes: int` - Font file size
- `sha1_checksum: str` - Font checksum

### 2. FontEmbeddingDecision (Policy Target)

**File**: `core/policy/targets.py:311`

**Structure**:
```python
@dataclass(frozen=True)
class FontEmbeddingDecision(PolicyDecision):
    font_family: str = ""
    font_size_bytes: int = 0
    sha1_checksum: str = ""
    should_embed: bool = True

    @classmethod
    def embed(cls, reasons, **kwargs) -> 'FontEmbeddingDecision':
        return cls(use_native=True, should_embed=True, reasons=reasons, **kwargs)

    @classmethod
    def skip(cls, reasons, **kwargs) -> 'FontEmbeddingDecision':
        return cls(use_native=True, should_embed=False, reasons=reasons, **kwargs)
```

### 3. DecisionReason (Enum)

**File**: `core/policy/targets.py:52`

**New Reasons**:
```python
class DecisionReason(Enum):
    # Font embedding reasons
    CUSTOM_FONT_REQUIRED = "custom_font_required"
    FONT_ALREADY_EMBEDDED = "font_already_embedded"
    FONT_SIZE_LIMIT_EXCEEDED = "font_size_limit_exceeded"
    EMBEDDING_DISABLED = "embedding_disabled"
```

### 4. PolicyConfig (Configuration)

**File**: `core/policy/config.py:73`

**New Settings**:
```python
@dataclass
class PolicyConfig:
    # Feature flags
    enable_font_embedding: bool = True

    # Font embedding configuration
    max_font_size_mb: float = 10.0  # Maximum font file size
```

### 5. SVGFontEmbedCoordinator (Executor)

**File**: `core/fonts/embed_coordinator.py:17`

**Role**: Execute policy decisions (no business logic)

```python
class SVGFontEmbedCoordinator:
    def __init__(self, policy=None):
        self.policy = policy
        self._seen_sha: set = set()  # Tracking only

    def harvest_and_embed(self, svg_string, pptx_path):
        all_faces = extract_embedded_faces(svg_string)
        faces_to_embed = []

        for face in all_faces:
            if self.policy:
                # Ask policy for decision
                decision = self.policy.decide_font_embedding(
                    font_family=face.family,
                    font_size_bytes=len(face.data),
                    sha1_checksum=face.sha1,
                    already_embedded=self._seen_sha
                )

                if decision.should_embed:
                    faces_to_embed.append(face)
                    self._seen_sha.add(face.sha1)  # Track
                    self.logger.debug(f"Policy: EMBED '{face.family}'")
            else:
                # Fallback: simple dedup (backward compat)
                if face.sha1 not in self._seen_sha:
                    faces_to_embed.append(face)
                    self._seen_sha.add(face.sha1)

        return embed_faces_into_pptx(pptx_path, faces_to_embed)
```

### 6. CleanSlateConverter (Integration)

**File**: `core/pipeline/converter.py:382`

**Wiring**:
```python
class CleanSlateConverter:
    def _initialize_components(self):
        # Initialize policy engine first
        policy_config = PolicyConfig()
        self.policy = PolicyEngine(policy_config)

        # Pass policy to font coordinator
        self.font_coordinator = SVGFontEmbedCoordinator(policy=self.policy)
```

---

## Decision Flow

```
SVG with @font-face
  ↓
[EXTRACT] Extract fonts from CSS
  → EmbeddedFace(family='ShinyCrystal', data=..., sha1='abc123')
  ↓
[POLICY] For each font:
  ├─ Check: sha1 in already_embedded?
  │    YES → FontEmbeddingDecision.skip(FONT_ALREADY_EMBEDDED)
  │    NO  → Continue
  ├─ Check: enable_font_embedding?
  │    NO  → FontEmbeddingDecision.skip(EMBEDDING_DISABLED)
  │    YES → Continue
  ├─ Check: font_size_bytes > max_font_size_mb?
  │    YES → FontEmbeddingDecision.skip(FONT_SIZE_LIMIT_EXCEEDED)
  │    NO  → Continue
  └─ Decision: FontEmbeddingDecision.embed(CUSTOM_FONT_REQUIRED)
  ↓
[EXECUTE] Coordinator executes decisions:
  → Embed fonts where decision.should_embed == True
  → Track embedded fonts in _seen_sha
  → Log decisions with reasons
  ↓
[PACKAGE] Obfuscate and write to PPTX
  → /ppt/fonts/fontN.odttf
  → /ppt/fontTable.xml
  ↓
PowerPoint-ready PPTX with embedded fonts
```

---

## Benefits of Policy-Driven Design

### 1. Consistency

All conversion decisions go through PolicyEngine:
- Path rendering: `decide_path()`
- Text rendering: `decide_text()`
- Group handling: `decide_group()`
- Image processing: `decide_image()`
- Filter strategy: `decide_filter_strategy()`
- **Font embedding: `decide_font_embedding()`** ← New

### 2. Configurability

Users can control font embedding via `PolicyConfig`:
```python
config = PolicyConfig(
    enable_font_embedding=False,  # Disable all embedding
    max_font_size_mb=5.0           # Stricter size limit
)
converter = CleanSlateConverter(config=config)
```

### 3. Transparency

Every decision includes `reasons` for debugging:
```python
decision = policy.decide_font_embedding(...)
print(decision.reasons)  # [DecisionReason.CUSTOM_FONT_REQUIRED]
```

### 4. Testability

Policy logic is isolated and unit-testable:
```python
def test_deduplication():
    policy = PolicyEngine()
    already_embedded = {'abc123'}

    decision = policy.decide_font_embedding(
        font_family='Arial',
        font_size_bytes=50000,
        sha1_checksum='abc123',
        already_embedded=already_embedded
    )

    assert decision.should_embed == False
    assert DecisionReason.FONT_ALREADY_EMBEDDED in decision.reasons
```

### 5. Extensibility

Easy to add new decision factors:
- Font licensing checks (OS/2 table fsType)
- Font format validation (TTF vs OTF)
- Per-font embedding rules (blacklist/whitelist)
- Usage-based subsetting decisions

---

## Configuration Examples

### Disable Font Embedding

```python
from core.pipeline.config import PipelineConfig
from core.policy.config import PolicyConfig

policy_config = PolicyConfig(enable_font_embedding=False)
pipeline_config = PipelineConfig()
pipeline_config.policy_config = policy_config

converter = CleanSlateConverter(config=pipeline_config)
# No fonts will be embedded
```

### Strict Size Limits

```python
policy_config = PolicyConfig(
    enable_font_embedding=True,
    max_font_size_mb=2.0  # Only fonts < 2MB
)

converter = CleanSlateConverter(...)
# Large fonts (e.g., CJK fonts) will be skipped
```

### Debug Font Decisions

```python
policy_config = PolicyConfig(
    enable_font_embedding=True,
    log_decisions=True  # Log all policy decisions
)

converter = CleanSlateConverter(...)
# Output:
# DEBUG: Policy decision: EMBED font 'ShinyCrystal' (50260 bytes, reasons: ['custom_font_required'])
# DEBUG: Policy decision: SKIP font 'Arial' (reasons: ['font_already_embedded'])
```

---

## Backward Compatibility

The coordinator maintains fallback behavior when policy is not provided:

```python
# Without policy (backward compatible)
coordinator = SVGFontEmbedCoordinator()  # No policy
coordinator.harvest_and_embed(svg, pptx)
# Uses simple SHA-1 deduplication, no size limits
```

```python
# With policy (new behavior)
coordinator = SVGFontEmbedCoordinator(policy=policy_engine)
coordinator.harvest_and_embed(svg, pptx)
# Uses full policy-driven decisions
```

---

## Testing

### Unit Tests for Policy

**File**: `tests/unit/policy/test_font_embedding_decisions.py` (to be created)

```python
def test_font_embedding_decision_embed():
    """Test decision to embed custom font"""
    policy = PolicyEngine()

    decision = policy.decide_font_embedding(
        font_family='CustomFont',
        font_size_bytes=50000,
        sha1_checksum='new123',
        already_embedded=set()
    )

    assert decision.should_embed == True
    assert DecisionReason.CUSTOM_FONT_REQUIRED in decision.reasons

def test_font_embedding_decision_dedup():
    """Test deduplication via SHA-1"""
    policy = PolicyEngine()
    already = {'abc123'}

    decision = policy.decide_font_embedding(
        font_family='Arial',
        font_size_bytes=50000,
        sha1_checksum='abc123',
        already_embedded=already
    )

    assert decision.should_embed == False
    assert DecisionReason.FONT_ALREADY_EMBEDDED in decision.reasons

def test_font_embedding_disabled():
    """Test embedding disabled via config"""
    config = PolicyConfig(enable_font_embedding=False)
    policy = PolicyEngine(config)

    decision = policy.decide_font_embedding(
        font_family='CustomFont',
        font_size_bytes=50000,
        sha1_checksum='new123',
        already_embedded=set()
    )

    assert decision.should_embed == False
    assert DecisionReason.EMBEDDING_DISABLED in decision.reasons

def test_font_size_limit():
    """Test size limit enforcement"""
    config = PolicyConfig(max_font_size_mb=0.01)  # 10KB limit
    policy = PolicyEngine(config)

    decision = policy.decide_font_embedding(
        font_family='HugeFont',
        font_size_bytes=50000,  # 50KB > 10KB
        sha1_checksum='new123',
        already_embedded=set()
    )

    assert decision.should_embed == False
    assert DecisionReason.FONT_SIZE_LIMIT_EXCEEDED in decision.reasons
```

### Integration Tests

```python
def test_coordinator_uses_policy():
    """Test coordinator respects policy decisions"""
    policy = PolicyEngine(PolicyConfig(enable_font_embedding=False))
    coordinator = SVGFontEmbedCoordinator(policy=policy)

    svg_with_font = '''<svg>
        <defs><style>@font-face { font-family: 'Custom'; src: url(data:...) }</style></defs>
    </svg>'''

    registry = coordinator.harvest_and_embed(svg_with_font, '/tmp/test.pptx')

    assert len(registry) == 0  # No fonts embedded (disabled by policy)
```

---

## Future Enhancements

### 1. Font Licensing Policy

```python
class PolicyEngine:
    def decide_font_embedding(self, ...):
        # Check OS/2 table fsType for embedding permissions
        if not font_allows_embedding(font_data):
            return FontEmbeddingDecision.skip(
                reasons=[DecisionReason.LICENSE_RESTRICTION]
            )
```

### 2. Font Format Policy

```python
# Only embed TTF/OTF, skip WOFF
if font_format not in ['truetype', 'opentype']:
    return FontEmbeddingDecision.skip(
        reasons=[DecisionReason.UNSUPPORTED_FORMAT]
    )
```

### 3. Subsetting Policy

```python
# Embed only if subsetting is possible
if font_size > 1MB and not can_subset(font_data):
    return FontEmbeddingDecision.skip(
        reasons=[DecisionReason.SIZE_LIMIT_NO_SUBSET]
    )
```

### 4. Whitelist/Blacklist Policy

```python
config = PolicyConfig(
    font_embedding_whitelist=['CustomFont1', 'CustomFont2'],
    font_embedding_blacklist=['ProprietaryFont']
)

if font_family in config.font_embedding_blacklist:
    return FontEmbeddingDecision.skip(
        reasons=[DecisionReason.BLACKLISTED_FONT]
    )
```

---

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Deduplication** | Hardcoded in coordinator | Policy-driven decision |
| **Configuration** | None | `enable_font_embedding`, `max_font_size_mb` |
| **Size Limits** | None | Configurable (10MB default) |
| **Reasoning** | Not captured | `DecisionReason` enum |
| **Testability** | Integration tests only | Unit testable policy logic |
| **Extensibility** | Modify coordinator code | Add policy rules |
| **Consistency** | Separate from other decisions | Unified with path/text/image decisions |
| **Logging** | Minimal | Detailed decision logging |

---

## Summary

✅ **Separation of Concerns**: Policy makes decisions, coordinator executes
✅ **Configurable**: `enable_font_embedding`, `max_font_size_mb` via `PolicyConfig`
✅ **Transparent**: Every decision has explicit `reasons`
✅ **Testable**: Policy logic is isolated and unit-testable
✅ **Consistent**: Follows same pattern as path/text/image decisions
✅ **Extensible**: Easy to add new decision factors (licensing, format, etc.)
✅ **Backward Compatible**: Fallback to simple dedup when policy not provided

---

**Result**: Font embedding is now a **first-class policy decision**, following the same architecture as all other conversion decisions in SVG2PPTX.

---

*Font Embedding Policy Architecture - SVG2PPTX v1.0.0*
*Date: 2025-10-02*
