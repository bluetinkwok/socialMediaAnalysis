# Frontend Scripts

This folder contains build, deployment, and utility scripts for the React frontend.

## Script Categories

### Build & Deployment
- `build.sh` - Production build script
- `deploy.sh` - Deploy to staging/production
- `pre-commit.sh` - Pre-commit hooks for code quality
- `optimize-assets.sh` - Optimize images and static assets

### Development Utilities
- `dev-setup.sh` - Setup development environment
- `generate-types.ts` - Generate TypeScript types from API
- `update-deps.sh` - Update and audit dependencies
- `test-coverage.sh` - Generate test coverage reports

### Asset Management
- `compress-images.sh` - Compress image assets
- `generate-icons.sh` - Generate icon sets from SVGs
- `update-favicons.sh` - Update favicon assets
- `audit-assets.sh` - Check for unused assets

### Code Quality
- `lint-fix.sh` - Auto-fix linting issues
- `type-check.sh` - Run TypeScript type checking
- `format-code.sh` - Format code with Prettier
- `analyze-bundle.sh` - Analyze bundle size

### Testing
- `run-e2e.sh` - Run end-to-end tests
- `visual-regression.sh` - Run visual regression tests
- `accessibility-test.sh` - Run accessibility audits
- `performance-test.sh` - Run performance audits

## Usage

Run scripts from the frontend root directory:
```bash
cd frontend
./scripts/script_name.sh
# or
npm run script-name  # if defined in package.json
```

## Node.js Scripts

Some scripts are also available as npm scripts in `package.json`:
```bash
npm run build
npm run test
npm run lint
npm run type-check
``` 