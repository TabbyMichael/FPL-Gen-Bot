#!/usr/bin/env python3
"""
Database migration script for FPL Bot
"""

import os
import sys
import sqlite3
from sqlalchemy import create_engine, text
from config.database import DATABASE_URL, Base, engine

def backup_database(db_path):
    """Create a backup of the existing database"""
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        print(f"Creating backup of database to {backup_path}")
        # Simple file copy for SQLite
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print("Backup created successfully")
        return backup_path
    else:
        print("No existing database found, skipping backup")
        return None

def migrate_sqlite_database():
    """Migrate SQLite database by recreating tables"""
    db_path = "./fpl_bot.db"
    
    # Create backup
    backup_database(db_path)
    
    # Drop all tables and recreate them with new schema
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Recreating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    
    print("Database migration completed successfully")

def migrate_postgresql_database():
    """Migrate PostgreSQL database by adding new columns"""
    # For PostgreSQL, we can add columns if they don't exist
    print("Migrating PostgreSQL database...")
    
    # List of new columns to add
    new_columns = [
        "yellow_cards INTEGER",
        "red_cards INTEGER", 
        "saves INTEGER",
        "bonus INTEGER",
        "bps INTEGER",
        "form FLOAT",
        "points_per_game FLOAT",
        "selected_by_percent FLOAT",
        "transfers_in INTEGER",
        "transfers_out INTEGER"
    ]
    
    with engine.connect() as conn:
        for column_def in new_columns:
            try:
                # Try to add column (will fail if it already exists)
                sql = f"ALTER TABLE player_performance ADD COLUMN {column_def}"
                conn.execute(text(sql))
                print(f"Added column: {column_def}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"Column already exists: {column_def}")
                else:
                    print(f"Warning: Could not add column {column_def}: {e}")
        
        conn.commit()
    
    print("PostgreSQL migration completed")

def main():
    """Main migration function"""
    print("FPL Bot Database Migration")
    print("=" * 30)
    
    if "sqlite" in DATABASE_URL.lower():
        print("SQLite database detected")
        migrate_sqlite_database()
    elif "postgresql" in DATABASE_URL.lower():
        print("PostgreSQL database detected")
        migrate_postgresql_database()
    else:
        print(f"Unsupported database type in URL: {DATABASE_URL}")
        return 1
    
    print("\nMigration completed successfully!")
    print("You can now run the bot normally.")
    return 0

if __name__ == "__main__":
    sys.exit(main())