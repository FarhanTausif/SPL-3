#!/usr/bin/env python3
"""Setup test database for development/testing without PostgreSQL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from alembic.config import Config
from alembic.command import upgrade

from dehalu.state.models import Base


def setup_sqlite_test_db(db_url: str = "sqlite:///./dehalu_test.db") -> None:
    """Create and initialize test database."""
    print(f"Setting up test database: {db_url}")
    
    # Create engine and tables
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    
    print("✓ Tables created")
    print("  - runs")
    print("  - evidence")
    print("  - run_events")
    print("\nTest database ready!")
    print(f"Set: DEHALU_DATABASE_URL={db_url}")


if __name__ == "__main__":
    setup_sqlite_test_db()
