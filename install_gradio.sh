#!/bin/bash
# Quick installer for Gradio UI support

echo "================================================"
echo "Installing Gradio UI Support"
echo "================================================"
echo ""

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "Consider activating your venv first:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Installing Gradio..."
pip install gradio>=4.0.0

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Gradio installed successfully!"
    echo ""
    echo "You can now launch the UI with:"
    echo "  python launch_ui.py"
    echo ""
    echo "Or:"
    echo "  python src/gradio_app.py"
    echo ""
else
    echo ""
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
