#!/bin/bash

# Update the system
apt update && apt upgrade -y

# Install Node.js 20.x (if not already installed)
if ! command -v node &> /dev/null || [[ $(node --version | cut -d'.' -f1 | sed 's/v//') -lt 18 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
fi

# Verify Node.js and npm versions
node --version
npm --version

# Configure npm for global installs without sudo
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=$HOME/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

npm install -g sharp --build-from-source
npm install -g --build-from-source @anthropic-ai/claude-code --verbose
export PATH=$PATH:/root/.npm-global/bin

# Verify installation with doctor command
if command -v claude &> /dev/null; then
    claude doctor
else
    echo "Claude installation failed. Check npm logs."
fi

echo "Installation complete. Run 'claude' to start using it."
