#!/bin/bash
# Test script to demonstrate debug mode vs normal mode

echo "=========================================="
echo "Test 1: Running WITHOUT --debug flag"
echo "=========================================="
echo ""
echo "Expected: Only see final answer, no verbose output"
echo "          Verbose output saved to logs/ directory"
echo ""
echo "Running: ./run.sh chat --query 'What is CUDA-Q?'"
echo ""

# This would run the actual test (commented out for now)
# ./run.sh chat --query "What is CUDA-Q?"

echo ""
echo "=========================================="
echo "Test 2: Running WITH --debug flag"
echo "=========================================="
echo ""
echo "Expected: See ALL verbose output including crew thinking"
echo ""
echo "Running: ./run.sh chat --debug --query 'What is CUDA-Q?'"
echo ""

# This would run the actual test (commented out for now)
# ./run.sh chat --debug --query "What is CUDA-Q?"

echo ""
echo "=========================================="
echo "How to test manually:"
echo "=========================================="
echo ""
echo "1. Normal mode (clean output):"
echo "   ./run.sh chat"
echo "   Then type a question and see clean output"
echo ""
echo "2. Debug mode (verbose output):"
echo "   ./run.sh chat --debug"
echo "   Then type a question and see all the crew agent thinking"
echo ""
echo "3. Check logs directory for captured output:"
echo "   ls -lh logs/"
echo ""
