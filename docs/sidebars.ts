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
  // Main documentation sidebar - simplified to only include existing files
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
      label: 'API Reference', 
      items: [
        'api/core-functions',
      ],
    },
    'contributing',
  ],
};

export default sidebars;
