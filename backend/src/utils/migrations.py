"""
Migration management utilities for the Video Subtitle Scraper database.

This module provides utilities for managing database schema migrations
following the strategy outlined in task 2-2-db-schema.md
"""

import os
import sqlite3
from typing import List, Dict
from db.models import DATABASE_PATH, check_migration_status, apply_migration
from utils.error_handler import log


def get_available_migrations() -> Dict[str, str]:
    """Get available migration files from the migrations directory"""
    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "migrations"
    )
    
    migrations = {}
    if os.path.exists(migrations_dir):
        for filename in sorted(os.listdir(migrations_dir)):
            if filename.endswith('.sql'):
                version = filename.replace('.sql', '')
                migrations[version] = os.path.join(migrations_dir, filename)
    
    return migrations


def run_pending_migrations() -> List[str]:
    """Run any pending migrations"""
    applied_migrations = check_migration_status()
    available_migrations = get_available_migrations()
    
    pending_migrations = []
    for version, filepath in available_migrations.items():
        if version not in applied_migrations and version != 'init':
            pending_migrations.append(version)
    
    if not pending_migrations:
        log('INFO', "No pending migrations")
        return []
    
    applied = []
    for version in pending_migrations:
        filepath = available_migrations[version]
        try:
            with open(filepath, 'r') as f:
                migration_sql = f.read()
            
            # Split into individual statements
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            if apply_migration(version, statements):
                log('INFO', f"Applied migration: {version}")
                applied.append(version)
            else:
                log('INFO', f"Migration {version} was already applied")
        
        except Exception as e:
            log('ERROR', f"Failed to apply migration {version}: {str(e)}")
            break  # Stop on first failure
    
    return applied


def migration_status() -> Dict:
    """Get migration status information"""
    applied_migrations = check_migration_status()
    available_migrations = get_available_migrations()
    
    pending = []
    for version in available_migrations.keys():
        if version not in applied_migrations and version != 'init':
            pending.append(version)
    
    return {
        'applied': applied_migrations,
        'available': list(available_migrations.keys()),
        'pending': pending
    }


def create_migration_template(version: str, description: str) -> str:
    """Create a new migration file template"""
    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "migrations"
    )
    
    filename = f"{version}_{description}.sql"
    filepath = os.path.join(migrations_dir, filename)
    
    template = f"""-- Migration: {version}
-- Description: {description}
-- Applied at: {"{datetime.now().isoformat()}"}

-- Add your migration SQL here
-- Example:
-- ALTER TABLE videos ADD COLUMN new_field TEXT;

-- Remember to test your migration before applying!
"""
    
    os.makedirs(migrations_dir, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(template)
    
    log('INFO', f"Created migration template: {filepath}")
    return filepath


if __name__ == "__main__":
    # Command line interface for migration management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrations.py [status|run|create]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        status = migration_status()
        print(f"Applied migrations: {status['applied']}")
        print(f"Available migrations: {status['available']}")
        print(f"Pending migrations: {status['pending']}")
    
    elif command == "run":
        applied = run_pending_migrations()
        if applied:
            print(f"Applied migrations: {applied}")
        else:
            print("No migrations to apply")
    
    elif command == "create":
        if len(sys.argv) < 4:
            print("Usage: python migrations.py create <version> <description>")
            sys.exit(1)
        
        version = sys.argv[2]
        description = sys.argv[3]
        filepath = create_migration_template(version, description)
        print(f"Created migration: {filepath}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
