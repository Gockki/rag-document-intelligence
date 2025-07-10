#!/usr/bin/env python3
"""
Quick test runner for Document Intelligence Platform
"""
import subprocess
import sys
import os

def run_tests():
    """Run all tests with nice output"""
    print("🧪 Document Intelligence Platform - Test Suite")
    print("=" * 60)
    
    if not os.path.exists("main.py"):
        print("❌ Please run this from the backend directory")
        return
    
    commands = [
        ("pytest --version", "Checking pytest installation"),
        ("pytest tests/ -v --tb=short", "Running all tests"),
        ("pytest --cov=. --cov-report=term-missing", "Coverage report")
    ]
    
    for cmd, desc in commands:
        print(f"\n🔍 {desc}")
        print("-" * 40)
        try:
            subprocess.run(cmd.split(), check=True)
            print(f"✅ {desc} - SUCCESS")
        except subprocess.CalledProcessError as e:
            print(f"❌ {desc} - FAILED (code: {e.returncode})")
        except FileNotFoundError:
            print(f"⚠️  Command not found: {cmd.split()[0]}")

if __name__ == "__main__":
    run_tests()
