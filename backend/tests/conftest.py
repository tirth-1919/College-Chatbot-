"""
Shared pytest configuration.

Historical note: the build machine exports a global DEBUG=release environment
variable. The application Settings now normalize unrecognized DEBUG values
safely (backend/app/core/config.py), so no environment mangling is required
here any more. This file is kept for future shared test fixtures.
"""
