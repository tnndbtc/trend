# AI Trend Intelligence Agent

An AI-powered agent that automatically collects, analyzes, and summarizes trending topics from multiple sources including Reddit, Hacker News, and Google News.

## Features

- **Django Web Interface**: Browse and visualize collected trends through an intuitive dashboard
- **Multi-Source Collection**: Gathers data from Reddit, Hacker News, and Google News
- **Smart Deduplication**: Uses embeddings and cosine similarity to remove duplicates
- **Intelligent Clustering**: Groups similar topics using machine learning
- **AI-Powered Summaries**: Leverages Claude AI to generate insightful trend summaries
- **Engagement Ranking**: Ranks trends by upvotes, comments, and scores
- **Persistent Storage**: SQLite database for tracking collection history
- **Fully Automatable**: Command-line tools for scheduled execution
- **Admin Interface**: Django admin for data management

## Project Structure

```
agent2/
├── trend_agent/           # Core trend collection engine
│   ├── main.py           # CLI orchestration script
│   ├── config.py         # Configuration settings
│   ├── models.py         # Pydantic data models
│   ├── collectors/       # Data collection modules
│   │   ├── reddit.py     # Reddit collector
│   │   ├── hackernews.py # Hacker News collector
│   │   └── google_news.py# Google News collector
│   ├── processing/       # Data processing pipeline
│   │   ├── normalize.py  # Text normalization
│   │   ├── deduplicate.py# Duplicate detection
│   │   ├── cluster.py    # Topic clustering
│   │   └── rank.py       # Cluster ranking
│   └── llm/              # LLM integration
│       ├── claude_client.py # Claude API client
│       └── summarizer.py # Trend summarization
│
└── web_interface/         # Django web application
    ├── manage.py         # Django management script
    ├── web_interface/    # Django project settings
    │   ├── settings.py   # Django configuration
    │   ├── urls.py       # URL routing
    │   └── wsgi.py       # WSGI application
    ├── trends_viewer/    # Main Django app
    │   ├── models.py     # Database models
    │   ├── views.py      # View logic
    │   ├── urls.py       # App URL patterns
    │   ├── admin.py      # Admin interface config
    │   ├── templates/    # HTML templates
    │   └── management/   # Custom commands
    │       └── commands/
    │           └── collect_trends.py # Trend collection command
    └── static/           # Static files (CSS, JS)
```

## Installation

### Quick Start with Docker (Recommended) 🐳

The fastest way to get started is using Docker:

1. **Prerequisites**: Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

2. **Setup environment**:
   ```bash
   cp .env.docker.example .env.docker
   # Edit .env.docker and add your CLAUDE_API_KEY
   ```

3. **Run setup script**:
   ```bash
   ./setup.sh
   ```

That's it! The script will:
- Build the Docker image
- Start the container
- Run database migrations
- Create a superuser
- Start the web server at http://localhost:11800

**Collect trends**:
```bash
docker-compose exec web python manage.py collect_trends --max-trends 20
```

**Useful Docker commands**:
```bash
docker-compose logs -f          # View logs
docker-compose down             # Stop containers
docker-compose restart          # Restart service
docker-compose exec web bash   # Shell access
```

---

### Manual Installation (Without Docker)

If you prefer to run without Docker:

### 1. Clone the repository

```bash
cd /home/tnnd/data/code/agent2
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the example environment file and add your Claude API key:

```bash
cp .env.example .env
```

Edit `.env` and add your Claude API key:

```
CLAUDE_API_KEY=your_api_key_here
MODEL=claude-sonnet-4-5-20250929
MAX_TRENDS=30
EMBED_MODEL=all-MiniLM-L6-v2
```

## Usage

### Option 1: Web Interface (Recommended)

The project includes a Django web interface for viewing and managing collected trends.

#### Setup Django

1. Navigate to the web interface directory:
```bash
cd web_interface
```

2. Run database migrations:
```bash
python manage.py migrate
```

3. Create a superuser (for admin access):
```bash
python manage.py createsuperuser
```

4. Start the development server:
```bash
python manage.py runserver
```

5. Open your browser to `http://localhost:11800`

#### Collect Trends via Django

Run the trend collection command:
```bash
python manage.py collect_trends --max-trends 20
```

Options:
- `--max-trends N`: Limit the number of trends to summarize (default: 20)

The command will:
1. Collect trending topics from all sources
2. Process and analyze the data
3. Save everything to the database
4. Make it viewable in the web interface

#### Web Interface Features

- **Dashboard**: Overview of latest collection runs and top trends
- **Trends**: Browse all identified trends with AI-generated summaries
- **Topics**: View all collected topics, filter by source
- **History**: Review past collection runs with metrics
- **Admin**: Full Django admin interface for data management

### Option 2: Command Line

Run the trend analysis directly from the command line:

```bash
cd trend_agent
python main.py
```

The agent will:
1. Collect trending topics from Reddit, Hacker News, and Google News
2. Normalize and deduplicate the data
3. Cluster similar topics together
4. Rank clusters by engagement metrics
5. Generate AI-powered summaries for the top 20 trends
6. Display results in the console

### Sample Output

```
🔍 Collecting trending topics...
   Collected 120 topics

📝 Normalizing...
🔄 Deduplicating...
   95 unique topics after deduplication

🗂️  Clustering similar topics...
   Created 12 clusters

📊 Ranking by importance...

🔥 Top Trends:

================================================================================

#1
--------------------------------------------------------------------------------
Trend title: AI Model Breakthroughs
• Major tech companies announce new AI capabilities
• Focus on multimodal reasoning and tool use
• Increased performance on coding benchmarks

Recent developments show significant advances in AI model capabilities,
particularly in coding and reasoning tasks. Multiple companies have released
new models with improved performance.

Sources: 8 topics
--------------------------------------------------------------------------------
...
```

## Pipeline Flow

```
Scheduler → Collect → Normalize → Deduplicate → Cluster → Rank → Summarize → Output
```

## Configuration

Key settings in `config.py`:

- `CLAUDE_API_KEY`: Your Anthropic API key
- `MODEL`: Claude model to use (default: claude-sonnet-4-5-20250929)
- `MAX_TRENDS`: Maximum number of trends to analyze (default: 30)
- `EMBED_MODEL`: Sentence transformer model for embeddings (default: all-MiniLM-L6-v2)

## Data Sources

### Reddit
- Fetches top 50 posts from r/all in the last 24 hours
- Extracts title, description, upvotes, and comments

### Hacker News
- Fetches top 30 stories from Hacker News
- Extracts title, URL, and score

### Google News
- Fetches top 40 news items from Google News RSS
- Extracts title, summary, and publication time

## Future Extensions

- Viral prediction engine
- Early trend detection
- Multi-language fusion
- Time-series momentum tracking
- Topic forecasting
- Content strategy recommendation
- YouTube + TikTok idea generator

## Dependencies

### Core Dependencies
- `aiohttp` - Async HTTP requests
- `feedparser` - RSS feed parsing
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `scikit-learn` - Clustering and similarity
- `sentence-transformers` - Text embeddings
- `anthropic` - Claude API client
- `python-dotenv` - Environment variable management

### Web Interface Dependencies
- `Django` - Web framework
- `django-extensions` - Extended Django functionality
- `asgiref` - ASGI utilities

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
