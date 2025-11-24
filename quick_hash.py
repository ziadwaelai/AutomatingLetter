#!/usr/bin/env python3
"""Quick password hasher - one line output"""
from werkzeug.security import generate_password_hash
import sys

if len(sys.argv) > 1:
    print(generate_password_hash(sys.argv[1]))
else:
    password = input("Enter password: ").strip()
    if password:
        print(generate_password_hash(password))
