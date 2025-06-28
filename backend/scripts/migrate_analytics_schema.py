#!/usr/bin/env python3
"""
Migration script to update the analytics_data table with new fields
for enhanced analytics functionality.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text, inspect
from db.database import engine, SessionLocal
from db.models import Base, AnalyticsData

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_analytics_schema():
    """Migrate the analytics_data table to include new fields"""
    
    print("🔄 Starting analytics schema migration...")
    
    # List of new columns to add
    new_columns = [
        # Advanced metrics
        ("engagement_velocity", "FLOAT"),
        ("content_quality_score", "FLOAT"),
        ("audience_reach_score", "FLOAT"),
        ("interaction_depth_score", "FLOAT"),
        
        # Scoring breakdown components
        ("weighted_components", "JSON"),
        ("applied_bonuses", "JSON"),
        ("applied_penalties", "JSON"),
        ("platform_adjustment", "FLOAT"),
        ("confidence_score", "FLOAT"),
        
        # Enhanced comparative metrics
        ("overall_rank", "INTEGER"),
        
        # Enhanced time-based metrics
        ("days_since_publish", "INTEGER"),
        
        # Processing metadata
        ("algorithm_version", "VARCHAR(50) DEFAULT '1.0'"),
        ("processing_duration", "FLOAT"),
        ("data_quality_flags", "JSON"),
    ]
    
    with engine.connect() as connection:
        # Check if analytics_data table exists
        inspector = inspect(engine)
        if 'analytics_data' not in inspector.get_table_names():
            print("📋 Creating analytics_data table...")
            Base.metadata.create_all(engine)
            print("✅ Analytics_data table created successfully")
            return
        
        # Add missing columns
        columns_added = 0
        for column_name, column_type in new_columns:
            if not check_column_exists('analytics_data', column_name):
                try:
                    sql = f"ALTER TABLE analytics_data ADD COLUMN {column_name} {column_type}"
                    connection.execute(text(sql))
                    print(f"✅ Added column: {column_name}")
                    columns_added += 1
                except Exception as e:
                    print(f"❌ Error adding column {column_name}: {e}")
        
        # Add unique constraint on post_id if not exists
        try:
            # Check if constraint already exists
            constraints = inspector.get_unique_constraints('analytics_data')
            post_id_unique_exists = any(
                'post_id' in constraint['column_names'] 
                for constraint in constraints
            )
            
            if not post_id_unique_exists:
                connection.execute(text(
                    "ALTER TABLE analytics_data ADD CONSTRAINT uq_analytics_post_id UNIQUE (post_id)"
                ))
                print("✅ Added unique constraint on post_id")
        except Exception as e:
            print(f"⚠️  Note: Could not add unique constraint on post_id: {e}")
        
        # Add indexes for performance
        indexes_to_add = [
            ("idx_analytics_performance_score", "performance_score"),
            ("idx_analytics_platform_rank", "platform_rank"),
            ("idx_analytics_engagement_rate", "engagement_rate"),
            ("idx_analytics_analyzed_at", "analyzed_at"),
        ]
        
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('analytics_data')]
        
        for index_name, column_name in indexes_to_add:
            if index_name not in existing_indexes:
                try:
                    sql = f"CREATE INDEX {index_name} ON analytics_data ({column_name})"
                    connection.execute(text(sql))
                    print(f"✅ Added index: {index_name}")
                except Exception as e:
                    print(f"⚠️  Could not add index {index_name}: {e}")
        
        # Commit the changes
        connection.commit()
        
        print(f"🎉 Migration completed! Added {columns_added} new columns")

def verify_migration():
    """Verify that the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    inspector = inspect(engine)
    columns = inspector.get_columns('analytics_data')
    column_names = [col['name'] for col in columns]
    
    expected_columns = [
        'id', 'post_id', 'engagement_rate', 'performance_score',
        'virality_score', 'trend_score', 'engagement_velocity',
        'content_quality_score', 'audience_reach_score', 'interaction_depth_score',
        'weighted_components', 'applied_bonuses', 'applied_penalties',
        'platform_adjustment', 'confidence_score', 'platform_rank',
        'category_rank', 'overall_rank', 'peak_engagement_hour',
        'days_since_publish', 'success_patterns', 'content_features',
        'algorithm_version', 'processing_duration', 'data_quality_flags',
        'analyzed_at', 'created_at', 'updated_at'
    ]
    
    missing_columns = [col for col in expected_columns if col not in column_names]
    
    if missing_columns:
        print(f"❌ Missing columns: {missing_columns}")
    else:
        print("✅ All expected columns are present")
    
    print(f"📊 Total columns in analytics_data: {len(column_names)}")

if __name__ == "__main__":
    try:
        migrate_analytics_schema()
        verify_migration()
        print("\n🎉 Analytics schema migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1) 