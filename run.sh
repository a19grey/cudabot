#!/bin/bash
# Simple startup script for the AI Documentation Assistant

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 AI Documentation Assistant${NC}"
echo "================================"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run:${NC}"
    echo "python3 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import crewai" 2>/dev/null; then
    echo -e "${RED}❌ Dependencies not installed. Installing now...${NC}"
    pip install -r requirements.txt
fi

# Check arguments
if [ "$1" = "setup" ]; then
    echo -e "${YELLOW}🔧 Setting up CUDA-Q target...${NC}"
    # Pass through any additional arguments (like --force-crawl)
    shift
    python src/main.py setup --target cuda_q "$@"
elif [ "$1" = "chat" ]; then
    echo -e "${YELLOW}💬 Starting chat session...${NC}"
    # Pass through any additional arguments (like --debug)
    shift
    python src/main.py chat --target cuda_q "$@"
elif [ "$1" = "info" ]; then
    echo -e "${YELLOW}📋 Showing target information...${NC}"
    python src/main.py info
elif [ "$1" = "test" ]; then
    echo -e "${YELLOW}🧪 Running validation tests...${NC}"
    python validate_setup.py
else
    echo -e "${YELLOW}Usage:${NC}"
    echo "./run.sh setup              - Setup CUDA-Q target (crawl docs, create embeddings, hierarchical preprocessing)"
    echo "./run.sh setup --force-crawl - Force re-crawl and regenerate all artifacts"
    echo "./run.sh chat               - Start interactive chat with CUDA-Q assistant"
    echo "./run.sh chat --debug       - Start chat with verbose debug output"
    echo "./run.sh info               - Show information about available targets"
    echo "./run.sh test               - Run validation tests"
    echo ""
    echo -e "${YELLOW}Manual usage:${NC}"
    echo "source venv/bin/activate"
    echo "python src/main.py --help"
fi
