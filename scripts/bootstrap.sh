#!/bin/bash
# MacroIntel Platform Bootstrap Script
# Run from project root: bash scripts/bootstrap.sh

set -e

echo "🚀 MacroIntel Platform Bootstrap"
echo "================================="

# Check .env
if [ ! -f ".env" ]; then
  echo "📋 Creating .env from example..."
  cp .env.example .env
  echo "⚠️  Edit .env and add your FRED_API_KEY before running the pipeline!"
fi

# Start infrastructure
echo "🐘 Starting PostgreSQL and Redis..."
docker compose up postgres redis -d

# Wait for postgres
echo "⏳ Waiting for database..."
sleep 5

# Backend setup
echo "🐍 Setting up Python environment..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

cd ..

# Frontend setup
echo "⚛️  Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your FRED_API_KEY (free at fred.stlouisfed.org)"
echo "  2. Start backend:  cd backend && uvicorn app.main:app --reload"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Trigger pipeline: POST http://localhost:8000/api/v1/pipeline/run"
echo "  5. Open dashboard: http://localhost:3000"
echo ""
echo "Or use Docker: docker compose up"
