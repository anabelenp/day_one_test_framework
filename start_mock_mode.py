#!/usr/bin/env python3
"""
Start Mock Mode for Netskope SDET Framework

This script starts all necessary mock services for testing without real credentials:
- Mock Netskope API server
- LocalStack (for AWS services)
- Mock GCP services

Usage:
    python start_mock_mode.py
"""

import os
import sys
import subprocess
import time
import signal
import threading
from tests.utils.mock_server import start_mock_server

def check_dependencies():
    """Check if required dependencies are available"""
    print(" Checking dependencies...")
    
    # Check if LocalStack is available (optional)
    try:
        subprocess.run(['localstack', '--version'], 
                      capture_output=True, check=True)
        print(" LocalStack found (for AWS mocking)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  LocalStack not found - AWS services will use basic mocks")
        print("   Install with: pip install localstack")
        return False

def start_localstack():
    """Start LocalStack for AWS service mocking"""
    print(" Starting LocalStack for AWS services...")
    try:
        # Start LocalStack in the background
        process = subprocess.Popen([
            'localstack', 'start', '--host'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for LocalStack to start
        time.sleep(5)
        print(" LocalStack started on http://localhost:4566")
        return process
    except Exception as e:
        print(f" Failed to start LocalStack: {e}")
        return None

def print_mock_info():
    """Print information about mock mode"""
    print("\n" + "="*60)
    print(" NETSKOPE SDET FRAMEWORK - MOCK MODE")
    print("="*60)
    print("\n Mock Services Status:")
    print("    Mock Netskope API: http://localhost:8080")
    print("    Mock AWS Services: http://localhost:4566")
    print("    Mock GCP Credentials: ./config/mock-gcp-credentials.json")
    
    print("\n Test Commands:")
    print("   pytest tests/swg/ -v")
    print("   pytest tests/dlp/ -v") 
    print("   pytest tests/ztna/ -v")
    print("   pytest tests/firewall/ -v")
    print("   pytest tests/ --html=reports/test_report.html")
    
    print("\n View Test Reports:")
    print("   open reports/test_report.html")
    
    print("\n Configuration:")
    print("   MOCK_MODE: true (in config/env.yaml)")
    print("   No real API keys needed!")
    
    print("\n⏹  Press Ctrl+C to stop all mock services")
    print("="*60 + "\n")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n Shutting down mock services...")
    sys.exit(0)

def main():
    """Main function to start mock mode"""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print(" Starting Netskope SDET Framework in Mock Mode...")
    
    # Check dependencies
    has_localstack = check_dependencies()
    
    # Start LocalStack if available
    localstack_process = None
    if has_localstack:
        localstack_process = start_localstack()
    
    # Print mock information
    print_mock_info()
    
    try:
        # Start mock Netskope API server (this will block)
        start_mock_server(port=8080)
    except KeyboardInterrupt:
        print("\n Shutting down...")
    finally:
        # Clean up LocalStack if it was started
        if localstack_process:
            print(" Stopping LocalStack...")
            localstack_process.terminate()
            localstack_process.wait()
        
        print(" All mock services stopped")

if __name__ == '__main__':
    main()