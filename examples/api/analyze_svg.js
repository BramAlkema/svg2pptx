#!/usr/bin/env node
/**
 * SVG Analysis API Examples (JavaScript/Node.js)
 *
 * Demonstrates using the svg2pptx analysis endpoints from JavaScript.
 * Ideal for Figma plugin integration and web applications.
 *
 * Requirements:
 *   npm install node-fetch
 *
 * Usage:
 *   node examples/api/analyze_svg.js
 */

const fetch = require('node-fetch');

// API Configuration
const API_BASE_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key-here'; // Replace with your actual API key

/**
 * Analyze SVG content and get policy recommendations.
 *
 * @param {string} svgContent - SVG XML content
 * @returns {Promise<Object>} Analysis result
 */
async function analyzeSvg(svgContent) {
  const response = await fetch(`${API_BASE_URL}/analyze/svg`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      svg_content: svgContent,
      analyze_depth: 'detailed',
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Analysis failed: ${error.detail}`);
  }

  return response.json();
}

/**
 * Validate SVG content and check compatibility.
 *
 * @param {string} svgContent - SVG XML content
 * @param {boolean} strictMode - Enable strict validation
 * @returns {Promise<Object>} Validation result
 */
async function validateSvg(svgContent, strictMode = false) {
  const response = await fetch(`${API_BASE_URL}/analyze/validate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      svg_content: svgContent,
      strict_mode: strictMode,
    }),
  });

  // Note: Returns 400 for invalid SVG, 200 for valid
  const result = await response.json();

  if (!response.ok && response.status !== 400) {
    throw new Error(`Validation request failed: ${result.detail}`);
  }

  return result;
}

/**
 * Get supported SVG features and capabilities.
 *
 * @param {string|null} category - Optional category filter
 * @returns {Promise<Object>} Feature support matrix
 */
async function getSupportedFeatures(category = null) {
  const url = new URL(`${API_BASE_URL}/analyze/features/supported`);
  if (category) {
    url.searchParams.append('category', category);
  }

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Feature query failed: ${error.detail}`);
  }

  return response.json();
}

// Example Usage
async function main() {
  console.log('='.repeat(60));
  console.log('SVG2PPTX Analysis API Examples (JavaScript)');
  console.log('='.repeat(60));

  // Example 1: Analyze Simple SVG
  console.log('\n1. Analyzing Simple SVG:');
  console.log('-'.repeat(60));

  const simpleSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <rect x="10" y="10" width="80" height="80" fill="blue" />
      <circle cx="50" cy="50" r="30" fill="red" opacity="0.5" />
    </svg>
  `;

  try {
    const result = await analyzeSvg(simpleSvg);

    console.log(`Complexity Score: ${result.complexity_score}/100`);
    console.log(`Total Elements: ${result.element_counts.total_elements}`);
    console.log(`Recommended Policy: ${result.recommended_policy.target}`);
    console.log(`Confidence: ${(result.recommended_policy.confidence * 100).toFixed(0)}%`);

    console.log('\nReasons:');
    result.recommended_policy.reasons.forEach(reason => {
      console.log(`  - ${reason}`);
    });

    console.log('\nPerformance Estimate:');
    const perf = result.estimated_performance;
    console.log(`  Conversion Time: ${perf.conversion_time_ms}ms`);
    console.log(`  Output Size: ${perf.output_size_kb}KB`);
    console.log(`  Memory Usage: ${perf.memory_usage_mb}MB`);

    if (result.warnings && result.warnings.length > 0) {
      console.log('\nWarnings:');
      result.warnings.forEach(warning => {
        console.log(`  ⚠️  ${warning}`);
      });
    }
  } catch (error) {
    console.error(`❌ Analysis failed: ${error.message}`);
  }

  // Example 2: Validate SVG
  console.log('\n\n2. Validating SVG:');
  console.log('-'.repeat(60));

  const complexSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <defs>
        <filter id="complexFilter">
          <feGaussianBlur stdDeviation="5" />
          <feColorMatrix type="matrix" />
          <feComposite operator="over" />
          <feBlend mode="multiply" />
          <feMorphology operator="dilate" />
        </filter>
      </defs>
      <rect x="20" y="20" width="160" height="160" fill="blue" filter="url(#complexFilter)" />
    </svg>
  `;

  try {
    const validation = await validateSvg(complexSvg, false);

    console.log(`Valid: ${validation.valid}`);
    console.log(`Version: ${validation.version || 'N/A'}`);

    if (validation.errors && validation.errors.length > 0) {
      console.log('\nErrors:');
      validation.errors.forEach(error => {
        console.log(`  ❌ [${error.code}] ${error.message}`);
        if (error.suggestion) {
          console.log(`     💡 ${error.suggestion}`);
        }
      });
    }

    if (validation.warnings && validation.warnings.length > 0) {
      console.log('\nWarnings:');
      validation.warnings.forEach(warning => {
        console.log(`  ⚠️  [${warning.code}] ${warning.message}`);
        if (warning.suggestion) {
          console.log(`     💡 ${warning.suggestion}`);
        }
      });
    }

    if (validation.compatibility) {
      const compat = validation.compatibility;
      console.log('\nCompatibility:');
      console.log(`  PowerPoint 2016: ${compat.powerpoint_2016}`);
      console.log(`  PowerPoint 2019: ${compat.powerpoint_2019}`);
      console.log(`  PowerPoint 365:  ${compat.powerpoint_365}`);
      console.log(`  Google Slides:   ${compat.google_slides}`);

      if (compat.notes && compat.notes.length > 0) {
        console.log('\n  Notes:');
        compat.notes.forEach(note => {
          console.log(`    - ${note}`);
        });
      }
    }
  } catch (error) {
    console.error(`❌ Validation failed: ${error.message}`);
  }

  // Example 3: Query Feature Support
  console.log('\n\n3. Querying Supported Features:');
  console.log('-'.repeat(60));

  try {
    const features = await getSupportedFeatures();
    console.log(`API Version: ${features.version}`);
    console.log(`Last Updated: ${features.last_updated}`);
    console.log('\nCategories Available:');
    Object.keys(features.categories).forEach(category => {
      console.log(`  - ${category}`);
    });

    // Get specific category
    console.log('\n\n4. Filter Feature Details:');
    console.log('-'.repeat(60));
    const filterFeatures = await getSupportedFeatures('filters');
    console.log(`Support Level: ${filterFeatures.details.support_level}`);

    console.log('\nNative Support:');
    filterFeatures.details.native_support.forEach(filter => {
      console.log(`  ✅ ${filter}`);
    });

    console.log('\nEMF Fallback:');
    filterFeatures.details.emf_fallback.forEach(filter => {
      console.log(`  📦 ${filter}`);
    });

    console.log(`\nNotes: ${filterFeatures.details.notes}`);
  } catch (error) {
    console.error(`❌ Feature query failed: ${error.message}`);
  }

  // Example 5: Complete Workflow
  console.log('\n\n5. Complete Workflow (Validate → Analyze → Convert):');
  console.log('-'.repeat(60));

  const workflowSvg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <defs>
        <linearGradient id="grad1">
          <stop offset="0%" stop-color="red" />
          <stop offset="100%" stop-color="blue" />
        </linearGradient>
        <filter id="shadow">
          <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="black" />
        </filter>
      </defs>
      <rect x="20" y="20" width="160" height="160" fill="url(#grad1)" filter="url(#shadow)" />
      <text x="100" y="110" text-anchor="middle" font-size="24" fill="white">Hello</text>
    </svg>
  `;

  try {
    // Step 1: Validate
    console.log('Step 1: Validating SVG...');
    const validation = await validateSvg(workflowSvg);

    if (!validation.valid) {
      console.log('❌ SVG is invalid, cannot proceed');
      validation.errors?.forEach(error => {
        console.log(`  - ${error.message}`);
      });
      return;
    }

    console.log('✅ SVG is valid');

    // Step 2: Analyze
    console.log('\nStep 2: Analyzing SVG...');
    const analysis = await analyzeSvg(workflowSvg);

    const complexity = analysis.complexity_score;
    const policy = analysis.recommended_policy.target;

    console.log(`Complexity: ${complexity}/100`);
    console.log(`Recommended Policy: ${policy}`);

    // Step 3: Decide on conversion
    console.log('\nStep 3: Conversion Recommendation:');

    if (complexity < 30) {
      console.log("  🚀 Use 'speed' policy for fast conversion");
    } else if (complexity < 60) {
      console.log(`  ⚖️  Use 'balanced' policy (recommended: ${policy})`);
    } else {
      console.log("  🎨 Use 'quality' policy for best fidelity");
    }

    // Check for warnings
    if (analysis.warnings && analysis.warnings.length > 0) {
      console.log('\n  Considerations:');
      analysis.warnings.forEach(warning => {
        console.log(`    ⚠️  ${warning}`);
      });
    }

    console.log('\n✅ Ready to convert with recommended settings');
  } catch (error) {
    console.error(`❌ Workflow failed: ${error.message}`);
  }
}

// Run examples
main().catch(console.error);
