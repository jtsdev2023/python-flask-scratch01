#!/usr/bin/env python3
"""Development server entry point for the app package."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
