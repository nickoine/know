"""
Global pytest configuration and fixtures for the KYC project.

This file provides project-wide test fixtures, configuration, and utilities
that are available to all test files across the project.
"""
import os
import django


def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etc.settings')
    django.setup()