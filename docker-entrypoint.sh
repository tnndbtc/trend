#!/bin/bash
set -e

echo "🐳 Starting AI Trend Intelligence Agent..."

# Wait a moment for any dependencies to be ready
sleep 2

# Navigate to web_interface directory
cd /app/web_interface

# Ensure db directory exists for database persistence
mkdir -p db

# Run migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Create superuser if environment variables are set
if [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ] && [ -n "$ADMIN_EMAIL" ]; then
    echo "👤 Creating superuser..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DB_USER').exists():
    User.objects.create_superuser('$DB_USER', '$ADMIN_EMAIL', '$DB_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
fi

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "✅ Initialization complete!"
echo ""
echo "🌐 Web interface will be available at: http://localhost:11800"
echo "🔧 Admin interface at: http://localhost:11800/admin"
echo ""
echo "💡 To collect trends, run:"
echo "   docker-compose exec web python manage.py collect_trends --max-trends 20"
echo ""

# Execute the main command
exec "$@"
