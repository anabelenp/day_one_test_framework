#!/usr/bin/env python3
"""
Simple script to query test results from MongoDB
Usage:
    python scripts/query_test_results.py --stats
    python scripts/query_test_results.py --recent 10
    python scripts/query_test_results.py --failed
    python scripts/query_test_results.py --sessions
"""

import os
import sys
import argparse

try:
    from pymongo import MongoClient
except ImportError:
    print("Error: pymongo not installed. Install with: pip install pymongo")
    sys.exit(1)


def get_connection():
    """Get MongoDB connection using environment or defaults"""
    # Connection parameters
    host = os.getenv('MONGODB_HOST', 'localhost')
    port = int(os.getenv('MONGODB_PORT', '27017'))
    
    # Try different authentication approaches
    password = os.environ.get('MONGODB_PASSWORD', 'admin_2024')
    
    # Build URI
    uri = f"mongodb://{host}:{port}"
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        # Try to auth
        client.admin.authenticate('admin', password)
        return client
    except:
        # Try default without auth
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            return client
        except Exception as e:
            print(f"Cannot connect to MongoDB at {host}:{port}")
            print(f"Error: {e}")
            print("\nMake sure MongoDB is running:")
            print("  docker-compose -f docker-compose.local.yml up -d mongodb")
            sys.exit(1)


def query_stats(db, env):
    """Show overall statistics"""
    test_results = db.test_results
    test_sessions = db.test_sessions
    
    total = test_results.count_documents({'environment': env})
    passed = test_results.count_documents({'environment': env, 'status': 'passed'})
    failed = test_results.count_documents({'environment': env, 'status': 'failed'})
    skipped = test_results.count_documents({'environment': env, 'status': 'skipped'})
    
    print(f"\n=== Test Statistics ({env}) ===")
    print(f"Total tests: {total}")
    if total:
        print(f"Passed:  {passed} ({passed*100//total}%)")
        print(f"Failed:  {failed} ({failed*100//total}%)")
        print(f"Skipped: {skipped} ({skipped*100//total}%)")
    
    # Session stats
    sessions = list(test_sessions.find({'environment': env}).sort('timestamp', -1).limit(10))
    if sessions:
        rates = [s.get('success_rate', 0) for s in sessions]
        avg_rate = sum(rates) / len(rates) if rates else 0
        print(f"\nRecent sessions avg success rate: {avg_rate:.1f}%")


def query_recent(db, env, limit):
    """Show recent test results"""
    test_results = db.test_results
    
    print(f"\n=== Recent Test Results ({env}) ===")
    results = list(test_results.find({'environment': env}).sort('start_time', -1).limit(limit))
    
    for r in results:
        status = r.get('status', 'unknown')
        icon = '✅' if status == 'passed' else '❌' if status == 'failed' else '⏭️'
        name = r.get('test_name', r.get('test_file', 'unknown'))
        duration = r.get('duration', 0)
        print(f"{icon} {name} ({duration:.3f}s)")
        
        if r.get('error_message'):
            err = r['error_message'][:80] + '...' if len(r.get('error_message', '')) > 80 else r.get('error_message', '')
            print(f"   Error: {err}")


def query_failed(db, env):
    """Show only failed tests"""
    test_results = db.test_results
    
    print(f"\n=== Failed Tests ({env}) ===")
    results = list(test_results.find({'environment': env, 'status': 'failed'}).sort('start_time', -1).limit(20))
    
    if not results:
        print("No failed tests found!")
        return
    
    for r in results:
        name = r.get('test_name', r.get('test_file', 'unknown'))
        print(f"❌ {name}")
        if r.get('error_message'):
            err = r['error_message'][:100]
            print(f"   {err}")


def query_sessions(db, env):
    """Show session summaries"""
    test_sessions = db.test_sessions
    
    print(f"\n=== Recent Test Sessions ({env}) ===")
    sessions = list(test_sessions.find({'environment': env}).sort('timestamp', -1).limit(10))
    
    if not sessions:
        print("No sessions found!")
        return
    
    for s in sessions:
        ts = s.get('timestamp', 'unknown')
        total = s.get('total_tests', 0)
        passed = s.get('passed', 0)
        failed = s.get('failed', 0)
        rate = s.get('success_rate', 0)
        print(f"\n{ts}")
        print(f"  Tests: {total} | ✅ {passed} | ❌ {failed}")
        print(f"  Success rate: {rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Query test results from MongoDB')
    parser.add_argument('--stats', action='store_true', help='Show overall statistics')
    parser.add_argument('--recent', '-r', type=int, default=10, help='Number of recent results')
    parser.add_argument('--failed', '-f', action='store_true', help='Show only failed tests')
    parser.add_argument('--sessions', '-s', action='store_true', help='Show session summaries')
    parser.add_argument('--env', default='local', help='Environment (local, integration, etc)')
    
    args = parser.parse_args()
    
    try:
        client = get_connection()
        db = client.get_database()
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)
    
    if args.stats:
        query_stats(db, args.env)
    elif args.failed:
        query_failed(db, args.env)
    elif args.sessions:
        query_sessions(db, args.env)
    else:
        query_recent(db, args.env, args.recent)


if __name__ == '__main__':
    main()