/**
 * Figma Plugin Integration Example
 *
 * Demonstrates integrating svg2pptx analysis and conversion APIs
 * into a Figma plugin for direct Figma → PowerPoint export.
 *
 * This example shows the complete workflow:
 * 1. Export Figma selection/frame as SVG
 * 2. Validate SVG compatibility
 * 3. Analyze complexity and get policy recommendation
 * 4. Convert to PowerPoint
 * 5. Download or upload to Google Drive
 *
 * Usage in Figma Plugin:
 *   - Copy this code into your Figma plugin code.ts
 *   - Update API_BASE_URL and API_KEY
 *   - Call exportToPowerPoint() from your UI
 */

// ============================================================================
// Configuration
// ============================================================================

const SVG2PPTX_API = {
  baseUrl: 'https://your-api-domain.com',
  apiKey: 'your-api-key-here',
};

// ============================================================================
// API Client
// ============================================================================

class SVG2PPTXClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  /**
   * Validate SVG before conversion
   */
  async validate(svgContent) {
    const response = await fetch(`${this.baseUrl}/analyze/validate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        svg_content: svgContent,
        strict_mode: false,
      }),
    });

    return response.json();
  }

  /**
   * Analyze SVG complexity and get recommendations
   */
  async analyze(svgContent) {
    const response = await fetch(`${this.baseUrl}/analyze/svg`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
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
   * Convert SVG to PowerPoint
   */
  async convert(svgContent, options = {}) {
    const {
      policy = 'balanced',
      embedFonts = true,
      enableAnimations = false,
    } = options;

    const response = await fetch(`${this.baseUrl}/convert/svg`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        svg_content: svgContent,
        target: policy,
        embed_fonts: embedFonts,
        enable_animations: enableAnimations,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Conversion failed: ${error.detail}`);
    }

    // Return blob for download
    return response.blob();
  }

  /**
   * Upload to Google Drive
   */
  async uploadToDrive(svgContent, options = {}) {
    const response = await fetch(`${this.baseUrl}/batch/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        svg_content: svgContent,
        target: options.policy || 'balanced',
        drive_folder_id: options.folderId,
        filename: options.filename || 'figma-export.pptx',
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Upload failed: ${error.detail}`);
    }

    return response.json();
  }
}

// ============================================================================
// Figma Plugin Code
// ============================================================================

/**
 * Export selected Figma nodes to PowerPoint
 *
 * @param {Object} options - Export options
 * @param {string} options.policy - Conversion policy (speed, balanced, quality)
 * @param {boolean} options.validateFirst - Validate SVG before conversion
 * @param {boolean} options.uploadToDrive - Upload to Google Drive
 * @param {string} options.driveFolderId - Google Drive folder ID
 */
async function exportToPowerPoint(options = {}) {
  const {
    policy = null, // null = auto-detect
    validateFirst = true,
    uploadToDrive = false,
    driveFolderId = null,
  } = options;

  try {
    // Step 1: Get selected nodes
    const selection = figma.currentPage.selection;

    if (selection.length === 0) {
      figma.notify('Please select a frame or object to export', { error: true });
      return;
    }

    figma.notify('Exporting to SVG...');

    // Step 2: Export as SVG
    const node = selection[0];
    const svgString = await node.exportAsync({ format: 'SVG_STRING' });

    // Step 3: Validate (optional but recommended)
    const client = new SVG2PPTXClient(SVG2PPTX_API.baseUrl, SVG2PPTX_API.apiKey);

    if (validateFirst) {
      figma.notify('Validating SVG...');

      const validation = await client.validate(svgString);

      if (!validation.valid) {
        console.error('SVG validation errors:', validation.errors);

        // Show errors to user
        const errorMessages = validation.errors
          .map(e => `• ${e.message}`)
          .join('\n');

        figma.notify(
          `SVG validation failed:\n${errorMessages}`,
          { error: true, timeout: 10000 }
        );

        return;
      }

      // Show warnings (non-blocking)
      if (validation.warnings && validation.warnings.length > 0) {
        const warningMessages = validation.warnings
          .map(w => `• ${w.message}`)
          .join('\n');

        console.warn('SVG validation warnings:', warningMessages);
      }
    }

    // Step 4: Analyze and get policy recommendation
    let selectedPolicy = policy;

    if (!selectedPolicy) {
      figma.notify('Analyzing complexity...');

      const analysis = await client.analyze(svgString);

      selectedPolicy = analysis.recommended_policy.target;

      console.log('Analysis results:', {
        complexity: analysis.complexity_score,
        recommendedPolicy: selectedPolicy,
        reasons: analysis.recommended_policy.reasons,
      });

      figma.notify(
        `Complexity: ${analysis.complexity_score}/100 - Using '${selectedPolicy}' policy`,
        { timeout: 5000 }
      );
    }

    // Step 5: Convert or Upload
    if (uploadToDrive) {
      figma.notify('Uploading to Google Drive...');

      const filename = `${node.name.replace(/[^a-z0-9]/gi, '_')}.pptx`;

      const uploadResult = await client.uploadToDrive(svgString, {
        policy: selectedPolicy,
        folderId: driveFolderId,
        filename: filename,
      });

      figma.notify(
        `✅ Uploaded to Google Drive: ${uploadResult.file_name}`,
        { timeout: 8000 }
      );

      console.log('Upload result:', uploadResult);
    } else {
      figma.notify('Converting to PowerPoint...');

      const pptxBlob = await client.convert(svgString, {
        policy: selectedPolicy,
        embedFonts: true,
      });

      // Download file
      const filename = `${node.name.replace(/[^a-z0-9]/gi, '_')}.pptx`;
      downloadFile(pptxBlob, filename);

      figma.notify('✅ PowerPoint downloaded!', { timeout: 5000 });
    }
  } catch (error) {
    console.error('Export failed:', error);
    figma.notify(`Export failed: ${error.message}`, { error: true, timeout: 10000 });
  }
}

/**
 * Download blob as file (browser environment)
 */
function downloadFile(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ============================================================================
// Figma Plugin UI (ui.html)
// ============================================================================

/*
Example UI HTML for Figma Plugin:

<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 20px;
      margin: 0;
    }
    button {
      width: 100%;
      padding: 12px;
      margin: 8px 0;
      font-size: 14px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      background: #18A0FB;
      color: white;
      font-weight: 500;
    }
    button:hover {
      background: #0D8CE8;
    }
    .option {
      margin: 12px 0;
    }
    label {
      display: block;
      margin-bottom: 4px;
      font-size: 12px;
      font-weight: 500;
    }
    select {
      width: 100%;
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 13px;
    }
    .checkbox-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  </style>
</head>
<body>
  <h3>Export to PowerPoint</h3>

  <div class="option">
    <label for="policy">Conversion Quality:</label>
    <select id="policy">
      <option value="auto">Auto-detect (recommended)</option>
      <option value="speed">Speed (fast, basic features)</option>
      <option value="balanced">Balanced (recommended)</option>
      <option value="quality">Quality (best fidelity)</option>
    </select>
  </div>

  <div class="option">
    <div class="checkbox-wrapper">
      <input type="checkbox" id="validate" checked>
      <label for="validate" style="margin: 0;">Validate before export</label>
    </div>
  </div>

  <button id="export-local">Export to PowerPoint</button>
  <button id="export-drive" style="background: #34A853;">Upload to Google Drive</button>

  <script>
    document.getElementById('export-local').onclick = () => {
      const policy = document.getElementById('policy').value;
      const validate = document.getElementById('validate').checked;

      parent.postMessage({
        pluginMessage: {
          type: 'export',
          policy: policy === 'auto' ? null : policy,
          validateFirst: validate,
          uploadToDrive: false,
        }
      }, '*');
    };

    document.getElementById('export-drive').onclick = () => {
      const policy = document.getElementById('policy').value;
      const validate = document.getElementById('validate').checked;

      parent.postMessage({
        pluginMessage: {
          type: 'export',
          policy: policy === 'auto' ? null : policy,
          validateFirst: validate,
          uploadToDrive: true,
        }
      }, '*');
    };
  </script>
</body>
</html>
*/

// ============================================================================
// Message Handler (code.ts)
// ============================================================================

/*
figma.ui.onmessage = async (msg) => {
  if (msg.type === 'export') {
    await exportToPowerPoint({
      policy: msg.policy,
      validateFirst: msg.validateFirst,
      uploadToDrive: msg.uploadToDrive,
    });
  }
};

figma.showUI(__html__, { width: 320, height: 280 });
*/
