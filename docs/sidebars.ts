import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  // Main documentation sidebar
  tutorialSidebar: [
    'intro',
    'installation',
    'quick-start',
    {
      type: 'category',
      label: 'User Guide',
      items: [
        'user-guide/basic-usage',
        'user-guide/multi-slide',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/TECHNICAL_FOUNDATION',
        'architecture/ARCHITECTURE_REFERENCE',
        'architecture/TECHNICAL_DOCUMENTATION',
      ],
    },
    {
      type: 'category',
      label: 'Decision Records (ADRs)',
      items: [
        'decisions/ADR-001-lxml-mandate',
        'decisions/ADR-002-bottom-up-architecture',
        'decisions/ADR-003-three-tier-font-strategy',
        'decisions/ADR-004-svgo-python-port',
        'decisions/ADR-005-advanced-path-optimization',
        'decisions/ADR-006-preprocessing-pipeline-architecture',
      ],
    },
    {
      type: 'category',
      label: 'Technical Specifications',
      items: [
        'specifications/ADVANCED_OPTIMIZATIONS',
        'specifications/performance-optimization',
        'specifications/METADATA_STRATEGY',
      ],
    },
    {
      type: 'category',
      label: 'Implementation Guides',
      items: [
        'guides/oauth-setup',
        'guides/batch-processing',
        'guides/EXPANSION_FRAMEWORK',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api/core-functions',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/SVGO_ATTRIBUTION',
        'reference/LICENSE_ATTRIBUTION',
      ],
    },
    'contributing',
  ],
};

export default sidebars;
