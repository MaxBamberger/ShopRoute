#!/usr/bin/env python3
"""
Utility to export tables from the grocery_cache.db SQLite database to CSV format.

Usage:
    python export_data.py <table_name> [--output output.csv]
    python export_data.py --list  # List all available tables
    python export_data.py --help  # Show this help message
"""

import sqlite3
import csv
import sys
import argparse
from pathlib import Path

# Determine the database path (should be at repo root)
# File is in utils/ folder, so go up two levels to reach repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "backend" / "app" / "grocery_cache.db"


def get_connection():
    """Get a connection to the SQLite database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def list_tables():
    """List all tables in the database."""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    
    return tables


def export_table_to_csv(table_name: str, output_file: str = None):
    """
    Export a table from the database to a CSV file.
    
    Args:
        table_name: Name of the table to export
        output_file: Path to the output CSV file (default: <table_name>.csv)
    
    Returns:
        Path to the created CSV file
    """
    if output_file is None:
        output_file = f"{table_name}.csv"
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Validate table name (basic check to prevent SQL injection)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    if not cur.fetchone():
        conn.close()
        raise ValueError(f"Table '{table_name}' does not exist in the database")
    
    # Get column names
    cur.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cur.fetchall()]
    
    # Get all rows from the table
    cur.execute(f"SELECT * FROM {table_name};")
    rows = cur.fetchall()
    conn.close()
    
    # Write to CSV
    output_path = Path(output_file)
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(columns)
        
        # Write data rows
        writer.writerows(rows)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Export SQLite tables from grocery_cache.db to CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_data.py item_cache
  python export_data.py stores --output stores_backup.csv
  python export_data.py --list
        """
    )
    
    parser.add_argument(
        'table',
        nargs='?',
        help='Name of the table to export'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output CSV file path (default: <table_name>.csv)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available tables'
    )
    
    args = parser.parse_args()
    
    # Handle --list flag
    if args.list:
        try:
            tables = list_tables()
            if tables:
                print("Available tables in grocery_cache.db:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("No tables found in the database")
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Table name is required if not using --list
    if not args.table:
        parser.print_help()
        sys.exit(1)
    
    # Export the table
    try:
        output_path = export_table_to_csv(args.table, args.output)
        row_count = sum(1 for _ in open(output_path)) - 1  # Subtract 1 for header
        print(f"✓ Successfully exported '{args.table}' to {output_path}")
        print(f"  Rows exported: {row_count}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nUse '--list' to see available tables")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
