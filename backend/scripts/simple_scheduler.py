#!/usr/bin/env python
"""
Simple Monitoring Scheduler

This script provides a standalone implementation of the monitoring scheduler
that doesn't rely on existing code with circular dependencies.
"""

import sys
import os
import time
import logging
import argparse
import signal
import sqlite3
from datetime import datetime, timedelta
import schedule
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../logs/simple_scheduler.log'))
    ]
)
logger = logging.getLogger("simple_scheduler")

# Global flag to control the main loop
running = True

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../data/social_media_analysis.db')

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False

def get_db_connection():
    """Get a database connection"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create tables if they don't exist
    create_tables(conn)
    
    return conn

def create_tables(conn):
    """Create database tables if they don't exist"""
    cursor = conn.cursor()
    
    # Create monitoring_jobs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monitoring_jobs (
        id INTEGER PRIMARY KEY,
        job_id TEXT NOT NULL,
        name TEXT NOT NULL,
        platform TEXT NOT NULL,
        target_url TEXT NOT NULL,
        target_type TEXT NOT NULL,
        frequency TEXT NOT NULL,
        interval_minutes INTEGER,
        max_items_per_run INTEGER DEFAULT 10,
        status TEXT NOT NULL,
        last_run_at TIMESTAMP,
        next_run_at TIMESTAMP,
        total_runs INTEGER DEFAULT 0,
        successful_runs INTEGER DEFAULT 0,
        failed_runs INTEGER DEFAULT 0,
        notify_on_new_content BOOLEAN DEFAULT 1,
        notify_on_failure BOOLEAN DEFAULT 1,
        notification_email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create monitoring_runs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monitoring_runs (
        id INTEGER PRIMARY KEY,
        monitoring_job_id INTEGER NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT NOT NULL,
        items_found INTEGER DEFAULT 0,
        items_processed INTEGER DEFAULT 0,
        new_items_downloaded INTEGER DEFAULT 0,
        error_message TEXT,
        FOREIGN KEY (monitoring_job_id) REFERENCES monitoring_jobs (id)
    )
    ''')
    
    conn.commit()

def get_pending_jobs(conn):
    """Get all jobs that are due to run"""
    cursor = conn.cursor()
    now = datetime.now()
    
    cursor.execute('''
    SELECT * FROM monitoring_jobs
    WHERE status = 'active' AND next_run_at <= ?
    ''', (now,))
    
    return cursor.fetchall()

def process_job(conn, job):
    """Process a single monitoring job"""
    logger.info(f"Processing job: {job['job_id']} ({job['name']})")
    
    # Create a run record
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO monitoring_runs (monitoring_job_id, status)
    VALUES (?, ?)
    ''', (job['id'], "in_progress"))
    run_id = cursor.lastrowid
    conn.commit()
    
    try:
        # Simulate job execution
        logger.info(f"Simulating download for {job['target_url']}")
        time.sleep(1)  # Simulate work
        
        # Update job statistics
        cursor.execute('''
        UPDATE monitoring_jobs 
        SET 
            last_run_at = ?,
            total_runs = total_runs + 1,
            successful_runs = successful_runs + 1
        WHERE id = ?
        ''', (datetime.now(), job['id']))
        
        # Calculate next run time based on frequency
        interval_minutes = job['interval_minutes'] if 'interval_minutes' in job and job['interval_minutes'] is not None else None
        next_run = calculate_next_run_time(job['frequency'], interval_minutes)
        cursor.execute('''
        UPDATE monitoring_jobs SET next_run_at = ? WHERE id = ?
        ''', (next_run, job['id']))
        
        # Complete the run
        cursor.execute('''
        UPDATE monitoring_runs 
        SET 
            status = ?, 
            end_time = ?, 
            items_found = ?, 
            items_processed = ?,
            new_items_downloaded = ?
        WHERE id = ?
        ''', ("completed", datetime.now(), 5, 5, 3, run_id))
        
        logger.info(f"Job {job['job_id']} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing job {job['job_id']}: {str(e)}", exc_info=True)
        
        # Update job statistics
        cursor.execute('''
        UPDATE monitoring_jobs 
        SET 
            last_run_at = ?,
            total_runs = total_runs + 1,
            failed_runs = failed_runs + 1
        WHERE id = ?
        ''', (datetime.now(), job['id']))
        
        # Calculate next run time based on frequency
        interval_minutes = job['interval_minutes'] if 'interval_minutes' in job and job['interval_minutes'] is not None else None
        next_run = calculate_next_run_time(job['frequency'], interval_minutes)
        cursor.execute('''
        UPDATE monitoring_jobs SET next_run_at = ? WHERE id = ?
        ''', (next_run, job['id']))
        
        # Mark run as failed
        cursor.execute('''
        UPDATE monitoring_runs 
        SET 
            status = ?, 
            end_time = ?,
            error_message = ?
        WHERE id = ?
        ''', ("failed", datetime.now(), str(e), run_id))
    
    conn.commit()

def calculate_next_run_time(frequency, interval_minutes=None):
    """Calculate the next run time based on frequency"""
    now = datetime.now()
    
    if frequency == 'hourly':
        return now + timedelta(hours=1)
    elif frequency == 'daily':
        return now + timedelta(days=1)
    elif frequency == 'weekly':
        return now + timedelta(weeks=1)
    elif frequency == 'monthly':
        # Approximate a month as 30 days
        return now + timedelta(days=30)
    elif frequency == 'custom' and interval_minutes:
        return now + timedelta(minutes=interval_minutes)
    else:
        # Default to daily
        return now + timedelta(days=1)

def create_test_job(conn):
    """Create a test job for demonstration"""
    cursor = conn.cursor()
    
    # Check if we already have jobs
    cursor.execute('SELECT COUNT(*) FROM monitoring_jobs')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Create a test job
        job_id = str(uuid.uuid4())
        now = datetime.now()
        next_run = now - timedelta(minutes=1)  # Set to run 1 minute ago
        
        cursor.execute('''
        INSERT INTO monitoring_jobs 
        (job_id, name, platform, target_url, target_type, frequency, status, next_run_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id, 
            "Test YouTube Channel", 
            "youtube", 
            "https://www.youtube.com/channel/test", 
            "channel", 
            "hourly", 
            "active", 
            next_run
        ))
        
        conn.commit()
        logger.info(f"Created test job: {job_id}")

def process_jobs():
    """Process pending monitoring jobs"""
    logger.info("Checking for pending monitoring jobs...")
    
    # Get database connection
    conn = None
    try:
        conn = get_db_connection()
        
        # Get pending jobs
        pending_jobs = get_pending_jobs(conn)
        
        if pending_jobs:
            logger.info(f"Found {len(pending_jobs)} pending jobs")
            for job in pending_jobs:
                process_job(conn, job)
        else:
            logger.info("No pending jobs found")
            
    except Exception as e:
        logger.error(f"Error processing jobs: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple monitoring scheduler")
    parser.add_argument("--interval", type=int, default=60,
                        help="Check interval in seconds (default: 60)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--create-test", action="store_true", help="Create a test job")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting simple monitoring scheduler (interval: {args.interval} seconds)")
    
    # Create test job if requested
    if args.create_test:
        conn = get_db_connection()
        create_test_job(conn)
        conn.close()
    
    if args.once:
        # Run once and exit
        process_jobs()
    else:
        # Schedule the job to run at regular intervals
        schedule.every(args.interval).seconds.do(process_jobs)
        
        # Run immediately on startup
        process_jobs()
        
        # Run the scheduler loop
        while running:
            schedule.run_pending()
            time.sleep(1)
    
    logger.info("Simple monitoring scheduler stopped")

if __name__ == "__main__":
    main()
