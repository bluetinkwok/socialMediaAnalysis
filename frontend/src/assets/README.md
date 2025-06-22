# Frontend Assets

This folder contains static assets used by the React frontend application.

## Asset Categories

### Images
- `images/` - Static images (logos, backgrounds, illustrations)
- `icons/` - Icon sets and individual icons
- `avatars/` - Default user avatars and placeholders
- `screenshots/` - App screenshots for documentation

### Styling Assets
- `fonts/` - Custom web fonts
- `css/` - Global CSS files and themes
- `scss/` - SCSS/Sass source files
- `themes/` - Theme configuration files

### Media Assets
- `videos/` - Demo videos, tutorials, promotional content
- `audio/` - Sound effects, notification sounds
- `animations/` - Lottie animations, GIFs

### Data Assets
- `data/` - Static JSON data files
- `mock-data/` - Mock data for development/testing
- `translations/` - Internationalization files
- `configs/` - Frontend configuration files

### Brand Assets
- `brand/` - Brand guidelines, logos, color palettes
- `social/` - Social media assets (og:image, favicons)
- `marketing/` - Marketing materials and assets

## File Organization

```
frontend/src/assets/
├── images/
│   ├── logos/
│   ├── backgrounds/
│   ├── illustrations/
│   └── placeholders/
├── icons/
│   ├── social-platforms/
│   ├── ui-icons/
│   └── brand-icons/
├── styles/
│   ├── fonts/
│   ├── themes/
│   └── global.css
├── data/
│   ├── mock-data/
│   ├── constants/
│   └── configs/
└── brand/
    ├── logos/
    ├── colors.json
    └── typography.json
```

## Optimization Guidelines

### Images
- Use WebP format when possible
- Provide multiple sizes for responsive images
- Compress images before adding to repository
- Use SVG for icons and simple graphics

### Performance
- Lazy load large images
- Use appropriate image formats (WebP, AVIF)
- Minimize asset bundle size
- Consider CDN for large assets

### Naming Conventions
- Use kebab-case for file names
- Include size in filename when relevant (e.g., `logo-small.svg`)
- Use descriptive names (e.g., `hero-background.jpg`)
- Group related assets in subfolders

## Import Examples

```typescript
// Static imports
import logo from '@/assets/images/logos/main-logo.svg'
import heroImage from '@/assets/images/backgrounds/hero-bg.jpg'

// Dynamic imports for code splitting
const DemoVideo = lazy(() => import('@/assets/videos/demo.mp4'))

// JSON data
import mockPosts from '@/assets/data/mock-data/posts.json'
``` 