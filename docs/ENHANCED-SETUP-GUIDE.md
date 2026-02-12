# Enhanced Setup.sh Usage Guide

Your development hub for the Trend Intelligence Platform!

## 🎯 What's New?

The enhanced setup.sh provides **two ways to work**:

1. **Interactive Visual Menus** - Perfect for exploration and occasional use
2. **Command-Line Mode** - Fast direct access for daily development

## 🚀 Quick Start

### Try It Now!

```bash
# Make it executable
chmod +x setup-enhanced.sh scripts/*.sh

# Launch interactive mode
./setup-enhanced.sh
```

You'll see a beautiful visual interface:

```
╔══════════════════════════════════════════════════════╗
║  🌟  Trend Intelligence Platform - Dev Hub  🌟      ║
╚══════════════════════════════════════════════════════╝

Current Status:
  ✅ Branch: main (clean)
  🔄 Services: 3 running, 2 stopped
  ℹ️  Last update: 2 minutes ago

┌──────────────────────────────────────────────────────┐
│  Main Menu                                           │
└──────────────────────────────────────────────────────┘

  🚀 Quick Start
  1. Start Full Platform (All Services)
  2. Start Basic Setup (Web + Database Only)
  ...
```

## 💻 Interactive Mode Features

### Visual Feedback
- ✅ Green checkmarks for success
- ❌ Red X for errors
- ⚠️  Yellow warnings
- 🔄 Spinners for running tasks
- Progress indicators: [1/4] Step...

### Smart Behavior
- Shows current git branch and status
- Displays which services are running
- Health checks for each service
- Resource usage monitoring
- Context-aware suggestions

### Easy Navigation
- Number-based menu selection
- 0 to go back or exit
- Press Enter to continue prompts
- Ctrl+C to cancel operations

## ⚡ Command-Line Mode (Fast!)

For daily development, skip the menus and run commands directly:

### Development Commands

```bash
# Start individual services (runs locally, not Docker)
./setup-enhanced.sh dev-api          # API on :8000
./setup-enhanced.sh dev-web          # Web on :11800
./setup-enhanced.sh dev-crawler      # Crawler service
./setup-enhanced.sh dev-infra        # Just databases

# Example workflow
./setup-enhanced.sh dev-infra        # Start PostgreSQL, Redis, Qdrant
./setup-enhanced.sh dev-api          # Then start API in another terminal
```

### Build Commands

```bash
# Build Docker images
./setup-enhanced.sh build            # All services
./setup-enhanced.sh build-api        # Just API
./setup-enhanced.sh build-web        # Just web
./setup-enhanced.sh build-crawler    # Just crawler
```

### Test Commands

```bash
# Run tests
./setup-enhanced.sh test             # All tests
./setup-enhanced.sh test-api         # API tests only
./setup-enhanced.sh test-web         # Web tests only
```

### Docker Commands

```bash
# Docker Compose operations
./setup-enhanced.sh up               # Start all services
./setup-enhanced.sh down             # Stop all services
./setup-enhanced.sh logs             # View all logs
./setup-enhanced.sh logs api         # View API logs only
./setup-enhanced.sh status           # Show running services
```

### Maintenance

```bash
# Code quality
./setup-enhanced.sh format           # Format code with black
./setup-enhanced.sh lint             # Lint with ruff
./setup-enhanced.sh clean            # Clean build artifacts

# Database
./setup-enhanced.sh migrate          # Run migrations
```

### Get Help

```bash
./setup-enhanced.sh help             # Show all commands
```

## 🔄 Parallel Development Workflow

Here's how to work on multiple services simultaneously:

### Terminal Setup (4 Terminals)

**Terminal 1 - Infrastructure**
```bash
./setup-enhanced.sh dev-infra
# Leaves running: PostgreSQL, Redis, Qdrant
```

**Terminal 2 - API Service**
```bash
cd /path/to/project
./setup-enhanced.sh dev-api
# API running on http://localhost:8000
# Hot reload enabled - edit code and see changes
```

**Terminal 3 - Web Interface**
```bash
cd /path/to/project
./setup-enhanced.sh dev-web
# Web running on http://localhost:11800
# Django dev server with auto-reload
```

**Terminal 4 - Crawler Service**
```bash
cd /path/to/project
./setup-enhanced.sh dev-crawler
# Crawler collecting data in background
```

### OR: Multiple Claude Code Instances

1. Open Claude Code instance in `services/api/`
   - Work on API endpoints
   - Run tests: `pytest tests/`
   - Local server: `../../setup-enhanced.sh dev-api`

2. Open Claude Code instance in `services/web-interface/`
   - Work on Django templates/views
   - Run tests: `pytest trends_viewer/tests/`
   - Local server: `../../setup-enhanced.sh dev-web`

3. Open Claude Code instance in `services/crawler/`
   - Add new collectors
   - Test crawler logic
   - Run: `../../setup-enhanced.sh dev-crawler`

Each instance works independently!

## 📚 Menu Structure

### Main Menu
```
Main Menu
├── 1-3:  🚀 Quick Start
├── 4-7:  💻 Development Mode
├── 8-9:  🏗️  Build & Install
├── 10:   🧪 Testing
├── 11-13: 📊 Monitor & Manage
├── 14-16: 🔧 Maintenance
├── 17-19: 📚 Information
└── 0:    Exit
```

### Quick Start (1-3)
- **1**: Full Platform - Everything running (API, Celery, Monitoring)
- **2**: Basic Setup - Just Web + Database (fastest start)
- **3**: Infrastructure - Just PostgreSQL, Redis, Qdrant

### Development Mode (4-7)
- **4**: Start API service locally
- **5**: Start Web interface locally
- **6**: Start Crawler service
- **7**: Start Translation service

### Build & Install (8-9)
- **8**: Build Docker images submenu
- **9**: Install dependencies submenu

### Testing (10)
- Run all tests
- Test specific services
- Code quality checks

### Monitor & Manage (11-13)
- **11**: Service status & health checks
- **12**: View logs (all or specific service)
- **13**: Start/stop individual services

### Maintenance (14-16)
- **14**: Database operations
- **15**: Clean old data
- **16**: Code quality (format, lint, typecheck)

### Information (17-19)
- **17**: Show all URLs and credentials
- **18**: Generate API keys
- **19**: CLI quick reference

## 🎨 Color Legend

When using the tool, you'll see:

- **🟢 Green (✅)**: Success, service running
- **🔴 Red (❌)**: Error, service stopped
- **🟡 Yellow (⚠️)**: Warning, needs attention
- **🔵 Blue (ℹ️)**: Information
- **🟣 Cyan**: Highlights, important info

## 🆚 Comparison: Old vs Enhanced

| Feature | Old setup.sh | Enhanced setup.sh |
|---------|-------------|-------------------|
| **Visual Design** | Basic colors | Rich colors + symbols + boxes |
| **Progress Feedback** | Limited | Step-by-step with spinners |
| **Service Status** | Manual check | Live status display |
| **Command-Line Mode** | ❌ No | ✅ Yes - fast access |
| **Health Checks** | Basic | Comprehensive |
| **Context Awareness** | ❌ No | ✅ Shows git status, running services |
| **Microservices Support** | Limited | ✅ Full - separate service dev |
| **Code Quality Tools** | ❌ No | ✅ Format, lint, typecheck |
| **Help System** | Manual | Built-in CLI reference |

## 💡 Pro Tips

### 1. Use Command-Line Mode for Speed
```bash
# Instead of menu navigation:
./setup-enhanced.sh dev-api    # Direct!
```

### 2. Chain Operations
```bash
# Build and start in one go
./setup-enhanced.sh build && ./setup-enhanced.sh up
```

### 3. Create Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias dev='./setup-enhanced.sh'
alias dev-api='./setup-enhanced.sh dev-api'
alias dev-web='./setup-enhanced.sh dev-web'

# Then just use:
dev-api    # Starts API
dev up     # Starts all services
```

### 4. Quick Status Check
```bash
# While working, quickly see what's running:
./setup-enhanced.sh status
```

### 5. Follow Logs in Real-Time
```bash
# Watch API logs while developing:
./setup-enhanced.sh logs api
```

## 🐛 Troubleshooting

### "Permission Denied" Error
```bash
chmod +x setup-enhanced.sh scripts/*.sh
```

### Helper Scripts Not Found
```bash
# Ensure you're in the repo root
cd /path/to/trend
./setup-enhanced.sh
```

### Makefile Not Found
```bash
# The enhanced setup.sh calls Makefile targets
# Make sure Makefile exists in the root directory
ls -la Makefile
```

### Service Won't Start
- Check logs: `./setup-enhanced.sh logs <service>`
- Check status: `./setup-enhanced.sh status`
- Try interactive mode for detailed error messages

## 🔮 Future Enhancements

Planned features:
- [ ] Auto-update dependencies
- [ ] One-command deployment
- [ ] Performance profiling
- [ ] Database seeding with test data
- [ ] Docker Compose profiles auto-detection
- [ ] Service dependency graph visualization

## 📖 Related Documentation

- [Architecture Overview](../README.new.md)
- [Service-Specific Docs](../services/)
- [Makefile Reference](../Makefile)
- [Migration Guide](./migration-guide.md)

---

**Enjoy your enhanced developer experience!** 🚀
