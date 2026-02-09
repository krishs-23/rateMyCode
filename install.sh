#!/bin/bash

# rateMyCode Installer

echo "Installing rateMyCode..."

# 1. Setup Python Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

echo "Installing Python dependencies..."
source venv/bin/activate
pip install -r engine/requirements.txt
deactivate

# 2. Compile Java
echo "Compiling Java Controller..."
rm -f src/RateMyCode.class # Clean
javac src/RateMyCode.java

# 3. Create Wrapper Script
echo "Creating wrapper script 'ratemycode'..."
INSTALL_DIR=$(pwd)
cat <<EOF > ratemycode
#!/bin/bash
# Wrapper for rateMyCode
# Usage: ./ratemycode [target_directory]

INSTALL_DIR="$INSTALL_DIR"
cd "\$INSTALL_DIR" # Java needs to run from root to find internal paths correctly via relative paths fallback
java -cp src RateMyCode "\${1:-.}"
EOF

chmod +x ratemycode

echo "-----------------------------------"
echo "Installation Complete!"
echo "Usage: ./ratemycode <path_to_project>"
echo "Example: ./ratemycode /Users/krish/my_project"
echo "-----------------------------------"
