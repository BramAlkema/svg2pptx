# SVG2PPTX Documentation Site

This directory contains the complete Docusaurus documentation site for SVG2PPTX.

## 🚀 Deployment to GitHub Pages (Root Domain)

To deploy this as your organization's main site at `https://svg2pptx.github.io`:

### 1. Create Organization Repository
```bash
# Create a new repository named exactly: svg2pptx.github.io
# This repository name must match your GitHub organization name
```

### 2. Copy Documentation Files
```bash
# Copy all files from this docs/ directory to the root of svg2pptx.github.io
cp -r docs/* path/to/svg2pptx.github.io/
cd path/to/svg2pptx.github.io/
```

### 3. Install Dependencies and Test
```bash
npm install
npm run build  # Test local build
npm run serve  # Test local serving
```

### 4. Enable GitHub Pages
- Go to repository Settings → Pages
- Set Source to "GitHub Actions"
- The workflow in `.github/workflows/deploy-docs.yml` will handle deployment

### 5. Deploy
```bash
git add .
git commit -m "Add SVG2PPTX documentation site"
git push origin main
```

## 🔧 Local Development

```bash
npm install     # Install dependencies
npm start       # Start development server
npm run build   # Build for production
npm run serve   # Serve production build
```

The site will be available at:
- **Development**: http://localhost:3000
- **Production**: https://svg2pptx.github.io

## 📝 Documentation Structure

- `docs/` - Documentation markdown files
- `src/` - React components and pages
- `static/` - Static assets
- `docusaurus.config.ts` - Configuration file
- `sidebars.ts` - Navigation structure

## 🎯 Features

- ✅ Custom homepage with SVG2PPTX branding
- ✅ Comprehensive documentation coverage
- ✅ Responsive design for all devices
- ✅ Automated deployment via GitHub Actions
- ✅ SEO optimized with proper meta tags
- ✅ Syntax highlighting for multiple languages
- ✅ Mobile-friendly navigation

## 🛠️ Customization

To modify the site:
- Edit content in `docs/` directory
- Customize homepage in `src/pages/index.tsx`
- Update features in `src/components/HomepageFeatures/`
- Modify styling in `src/css/custom.css`
- Update configuration in `docusaurus.config.ts`

The site will automatically rebuild and redeploy when you push changes to the main branch.
