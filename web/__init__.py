"""
DroneForge AI - Web Module
Flask-based web interface for drone design automation.
"""

from .app import app, create_app, run_server

__all__ = ["app", "create_app", "run_server"]
