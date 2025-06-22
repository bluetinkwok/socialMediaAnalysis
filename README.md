# Social Media Success Analysis Platform

A comprehensive platform for downloading, analyzing, and understanding successful social media content across multiple platforms (RedNote, Instagram, Threads, YouTube).

## 🎯 Project Overview

This platform helps creators, marketers, and businesses understand what makes content successful by:
- Downloading content from multiple social media platforms
- Analyzing engagement patterns and success metrics
- Providing insights for content strategy optimization
- Organizing content in a structured, searchable format

## 🏗️ Project Structure

```
socialMediaAnalysis/
├── backend/              # Python 3.12 FastAPI backend
│   ├── downloads/        # Downloaded content storage
│   │   ├── youtube/      # YouTube content (videos, thumbnails, text)
│   │   ├── instagram/    # Instagram content (posts, stories, reels)
│   │   ├── threads/      # Threads content (text, links)
│   │   └── rednote/      # RedNote content (mixed media)
│   ├── assets/           # Backend assets (configs, models, SSL certs)
│   ├── scripts/          # Backend utility scripts (DB, scraping, analytics)
│   └── tests/            # Backend unit tests
├── frontend/             # React TypeScript frontend
│   ├── src/
│   │   ├── assets/       # Frontend assets (images, styles, data)
│   │   └── tests/        # Frontend unit tests
│   └── scripts/          # Frontend build and deployment scripts
├── docker/               # Docker configuration files
└── docs/                 # Project documentation
```

## 🚀 Supported Platforms

- **YouTube**: Videos (shorts & long-form), thumbnails, metadata, transcripts
- **Instagram**: Posts, stories, reels, IGTV, comments, profile data
- **Threads**: Text posts, links, engagement metrics
- **RedNote**: Mixed content posts (text, images, videos)

## 🛠️ Technology Stack

### Backend (Python 3.12)
- **FastAPI** - Modern web framework
- **SQLite** - Database for metadata storage
- **yt-dlp** - YouTube content downloading
- **Selenium** - Web scraping automation
- **BeautifulSoup** - HTML parsing
- **pytest** - Testing framework

### Frontend (React TypeScript)
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Material-UI** - Component library
- **React Query** - Data fetching
- **Jest/RTL** - Testing

### Infrastructure
- **Docker Compose** - Container orchestration
- **SQLite** - Local database
- **File System** - Media storage

## 🔧 Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd socialMediaAnalysis

# Start with Docker Compose
docker-compose up --build

# Or run locally:
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm start
```

## 📋 Features

### Core Functionality
- [ ] Multi-platform content downloading
- [ ] Automated content analysis
- [ ] Success pattern identification
- [ ] Engagement metrics tracking
- [ ] Content organization system

### Security Features
- [ ] Input validation and sanitization
- [ ] Malware scanning for downloads
- [ ] Rate limiting and anti-abuse
- [ ] Authentication and authorization
- [ ] Data encryption and privacy

### Analytics Features
- [ ] Performance scoring algorithms
- [ ] Trend identification
- [ ] Comparative analysis
- [ ] Export capabilities
- [ ] Reporting dashboard

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests  
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 📚 Documentation

- [Product Requirements Document](.taskmaster/docs/prd.txt)
- [Security Requirements](.taskmaster/docs/security-requirements.md)
- [Testing Requirements](.taskmaster/docs/testing-requirements.md)
- [API Documentation](docs/api.md) - Coming soon
- [Deployment Guide](docs/deployment.md) - Coming soon

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is designed for educational and research purposes. Please respect platform terms of service and applicable laws when using this software. Always ensure you have permission to download and analyze content.

## 📞 Support

For questions, issues, or contributions, please:
- Open an issue on GitHub
- Check the documentation in the `docs/` folder
- Review the project tasks in `.taskmaster/`

---

**Status**: 🚧 In Development - See [Tasks](.taskmaster/tasks/) for current progress 