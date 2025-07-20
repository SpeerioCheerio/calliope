#!/usr/bin/env python3
"""
Calliope App Startup Script
This script handles the startup sequence for the Calliope vocabulary application.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def install_requirements():
    """Install required packages"""
    requirements_file = Path("backend/requirements.txt")
    
    if not requirements_file.exists():
        print("Error: requirements.txt not found in backend directory")
        return False
    
    print("Installing required packages...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        print("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def check_env_file():
    """Check if .env file exists and provide guidance"""
    env_file = Path("backend/.env")
    
    if not env_file.exists():
        print("\nWarning: .env file not found in backend directory")
        print("Please create a .env file with your OpenAI API key:")
        print("   cd backend")
        print("   cp env_template.txt .env")
        print("   # Edit .env and add your OpenAI API key")
        return False
    
    print(".env file found")
    return True

def start_backend():
    """Start the FastAPI backend server"""
    backend_dir = Path("backend")
    
    if not backend_dir.exists():
        print("Error: backend directory not found")
        return False
    
    print("\nStarting backend server...")
    try:
        # Change to backend directory and start the server
        os.chdir(backend_dir)
        
        # Start the FastAPI server
        subprocess.run([sys.executable, "main.py"], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error starting backend: {e}")
        return False
    except KeyboardInterrupt:
        print("\nShutting down...")
        return True

def main():
    """Main startup function"""
    print("Calliope Vocabulary App Startup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print("Failed to install requirements. Please install manually:")
        print("   cd backend")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Check environment file
    env_exists = check_env_file()
    if not env_exists:
        print("\nPlease set up your .env file before continuing.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("\n" + "=" * 40)
    print("Starting Calliope Application...")
    print("Frontend will be available at: http://localhost:8000/static/index.html")
    print("API documentation at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print("=" * 40)
    
    # Start the backend server
    if not start_backend():
        print("Failed to start backend server")
        sys.exit(1)

if __name__ == "__main__":
    main() 