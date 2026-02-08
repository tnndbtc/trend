# Quick Start Guide

Get the AI Trend Intelligence Agent running in 2 minutes!

## Method 1: Docker (Recommended) 🐳

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- An Anthropic API key

### Setup Steps

**1. Configure API Key**

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker` and add your key:
```
CLAUDE_API_KEY=sk-ant-xxxxx
```

**2. Run Setup Script**

```bash
./setup.sh
```

**3. Collect Trends**

```bash
docker-compose exec web python manage.py collect_trends --max-trends 20
```

**4. View Results**

Visit: http://localhost:11800

Default login:
- Username: `admin`
- Password: `changeme123`

### Docker Management

```bash
docker-compose logs -f          # View logs
docker-compose down             # Stop
docker-compose restart          # Restart
docker-compose exec web bash   # Shell access
```

---

## Method 2: Manual Installation

### Prerequisites

- Python 3.8+
- pip
- An Anthropic API key

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Copy the example environment file and add your Claude API key:

```bash
cp .env.example .env
```

Edit `.env` and add your key:
```
CLAUDE_API_KEY=sk-ant-xxxxx
```

### 3. Setup Database

```bash
cd web_interface
python manage.py migrate
python manage.py createsuperuser  # Follow prompts
```

### 4. Start Web Server

```bash
python manage.py runserver
```

Visit: http://localhost:11800

### 5. Collect Trends

In a new terminal:

```bash
cd web_interface
python manage.py collect_trends --max-trends 10
```

This will:
- Fetch topics from Reddit, Hacker News, and Google News
- Analyze and cluster them
- Generate AI summaries
- Save to database

### 6. View Results

Refresh your browser to see:
- Dashboard with latest trends
- Detailed trend analysis
- Source attribution
- Collection history

## Tips

- Run `collect_trends` on a schedule (cron/systemd) for continuous monitoring
- Access admin at http://localhost:11800/admin/
- Filter topics by source in the Topics view
- Each collection run is tracked with metrics

## Troubleshooting

**Database errors?**
- Make sure you ran `python manage.py migrate`

**No trends showing?**
- Run `python manage.py collect_trends` first

**Import errors?**
- Check all dependencies installed: `pip install -r requirements.txt`

**API errors?**
- Verify your CLAUDE_API_KEY in `.env`

## Next Steps

- Customize clustering parameters in `trend_agent/processing/cluster.py`
- Adjust deduplication threshold in `deduplicate.py`
- Modify the summary prompt in `llm/summarizer.py`
- Add new data sources in `collectors/`

Enjoy exploring trends!
