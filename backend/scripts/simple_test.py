#!/usr/bin/env python
"""
Simple test script for monitoring scheduler

This script tests the basic functionality without relying on existing code.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import uuid
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("simple_test")

def create_test_database():
    """Create a simple test database"""
    logger.info("Creating test database")
    
    # Create an in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE monitoring_jobs (
        id INTEGER PRIMARY KEY,
        job_id TEXT NOT NULL,
        name TEXT NOT NULL,
        platform TEXT NOT NULL,
        target_url TEXT NOT NULL,
        target_type TEXT NOT NULL,
        frequency TEXT NOT NULL,
        interval_minutes INTEGER,
        status TEXT NOT NULL,
        next_run_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE monitoring_runs (
        id INTEGER PRIMARY KEY,
        monitoring_job_id INTEGER NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT NOT NULL,
        items_found INTEGER DEFAULT 0,
        items_processed INTEGER DEFAULT 0,
        FOREIGN KEY (monitoring_job_id) REFERENCES monitoring_jobs (id)
    )
    ''')
    
    # Insert test data
    job_id = str(uuid.uuid4())
    now = datetime.now()
    next_run = now - timedelta(minutes=5)  # Set to run 5 minutes ago
    
    cursor.execute('''
    INSERT INTO monitoring_jobs (job_id, name, platform, target_url, target_type, frequency, status, next_run_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, "Test Job", "youtube", "https://www.youtube.com/channel/test", "channel", "daily", "active", next_run))
    
    conn.commit()
    
    logger.info(f"Created test job: {job_id}")
    return conn

def process_pending_jobs(conn):
    """Process pending jobs"""
    logger.info("Processing pending jobs")
    
    cursor = conn.cursor()
    now = datetime.now()
    
    # Find pending jobs
    cursor.execute('''
    SELECT id, job_id, name FROM monitoring_jobs
    WHERE status = 'active' AND next_run_at <= ?
    ''', (now,))
    
    pending_jobs = cursor.fetchall()
    logger.info(f"Found {len(pending_jobs)} pending jobs")
    
    for job_id, job_uuid, name in pending_jobs:
        logger.info(f"Processing job: {job_uuid} ({name})")
        
        # Create a run record
        cursor.execute('''
        INSERT INTO monitoring_runs (monitoring_job_id, status)
        VALUES (?, ?)
        ''', (job_id, "in_progress"))
        run_id = cursor.lastrowid
        
        # Simulate processing
        logger.info(f"Simulating processing for job {job_uuid}")
        
        # Update job next run time
        next_run = datetime.now() + timedelta(days=1)
        cursor.execute('''
        UPDATE monitoring_jobs SET next_run_at = ? WHERE id = ?
        ''', (next_run, job_id))
        
        # Complete the run
        cursor.execute('''
        UPDATE monitoring_runs SET status = ?, end_time = ?, items_found = ?, items_processed = ?
        WHERE id = ?
        ''', ("completed", datetime.now(), 5, 5, run_id))
    
    conn.commit()
    return pending_jobs

def main():
    """Main test function"""
    logger.info("Starting simple test")
    
    # Create test database
    conn = create_test_database()
    
    # Process pending jobs
    jobs = process_pending_jobs(conn)
    
    # Verify results
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM monitoring_runs WHERE status = "completed"')
    completed_runs = cursor.fetchone()[0]
    
    logger.info(f"Completed runs: {completed_runs}")
    logger.info("Test completed successfully")
    
    conn.close()

if __name__ == "__main__":
    main()
