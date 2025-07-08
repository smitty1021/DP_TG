#!/usr/bin/env python3
"""
Test Data Cleanup Script
========================
Removes all generated test data while preserving default tags and system data.
This script will delete:
- All trades and related data (entries, exits, images)
- All trading models
- All daily journal entries
- All user-created tags (preserving default tags only)

Usage: python cleanup_test_data.py
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    Trade, EntryPoint, ExitPoint, TradeImage,
    TradingModel, DailyJournal, DailyJournalImage,
    Tag, Instrument
)


def confirm_deletion():
    """Get user confirmation before proceeding with deletion."""

    print("⚠️  WARNING: DATA DELETION SCRIPT")
    print("=" * 50)
    print("This script will permanently delete:")
    print("• All trades and related data (entries, exits, images)")
    print("• All trading models")
    print("• All daily journal entries and images")
    print("• All user-created tags")
    print("• All instruments (optional)")
    print("")
    print("This will preserve:")
    print("• Default system tags (if any)")
    print("• User accounts")
    print("• Other system data")
    print("=" * 50)

    confirm1 = input("Are you sure you want to delete ALL test data? (yes/no): ").strip().lower()
    if confirm1 != 'yes':
        print("❌ Operation cancelled.")
        return False

    confirm2 = input("This action cannot be undone. Type 'DELETE' to confirm: ").strip()
    if confirm2 != 'DELETE':
        print("❌ Operation cancelled.")
        return False

    return True


def delete_trade_related_data(user_id=None):
    """Delete all trade-related data."""

    print("\n🗑️  Deleting trade-related data...")

    # Count existing data
    if user_id:
        trades_count = Trade.query.filter_by(user_id=user_id).count()
        entries_count = db.session.query(EntryPoint).join(Trade).filter(Trade.user_id == user_id).count()
        exits_count = db.session.query(ExitPoint).join(Trade).filter(Trade.user_id == user_id).count()
        trade_images_count = db.session.query(TradeImage).filter_by(user_id=user_id).count()
    else:
        trades_count = Trade.query.count()
        entries_count = EntryPoint.query.count()
        exits_count = ExitPoint.query.count()
        trade_images_count = TradeImage.query.count()

    print(
        f"   📊 Found: {trades_count} trades, {entries_count} entries, {exits_count} exits, {trade_images_count} images")

    if trades_count == 0:
        print("   ✅ No trades to delete")
        return

    try:
        # Delete in proper order to respect foreign key constraints

        # 1. Delete trade images first
        if user_id:
            deleted_images = db.session.query(TradeImage).filter_by(user_id=user_id).delete()
        else:
            deleted_images = db.session.query(TradeImage).delete()
        print(f"   🗑️  Deleted {deleted_images} trade images")

        # 2. Delete entry/exit points (will cascade from trades, but being explicit)
        if user_id:
            deleted_entries = db.session.query(EntryPoint).join(Trade).filter(Trade.user_id == user_id).delete(
                synchronize_session=False)
            deleted_exits = db.session.query(ExitPoint).join(Trade).filter(Trade.user_id == user_id).delete(
                synchronize_session=False)
        else:
            deleted_entries = db.session.query(EntryPoint).delete()
            deleted_exits = db.session.query(ExitPoint).delete()
        print(f"   🗑️  Deleted {deleted_entries} entry points")
        print(f"   🗑️  Deleted {deleted_exits} exit points")

        # 3. Delete trades (this should cascade to related data)
        if user_id:
            deleted_trades = db.session.query(Trade).filter_by(user_id=user_id).delete()
        else:
            deleted_trades = db.session.query(Trade).delete()
        print(f"   🗑️  Deleted {deleted_trades} trades")

        db.session.commit()
        print("   ✅ Trade data deletion completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error deleting trade data: {e}")
        raise


def delete_trading_models(user_id=None):
    """Delete all trading models."""

    print("\n🗑️  Deleting trading models...")

    if user_id:
        models_count = TradingModel.query.filter_by(user_id=user_id).count()
    else:
        models_count = TradingModel.query.count()

    print(f"   📊 Found: {models_count} trading models")

    if models_count == 0:
        print("   ✅ No trading models to delete")
        return

    try:
        if user_id:
            deleted_models = db.session.query(TradingModel).filter_by(user_id=user_id).delete()
        else:
            deleted_models = db.session.query(TradingModel).delete()

        print(f"   🗑️  Deleted {deleted_models} trading models")

        db.session.commit()
        print("   ✅ Trading models deletion completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error deleting trading models: {e}")
        raise


def delete_journal_data(user_id=None):
    """Delete all daily journal entries and related images."""

    print("\n🗑️  Deleting journal data...")

    if user_id:
        journals_count = DailyJournal.query.filter_by(user_id=user_id).count()
        journal_images_count = DailyJournalImage.query.filter_by(user_id=user_id).count()
    else:
        journals_count = DailyJournal.query.count()
        journal_images_count = DailyJournalImage.query.count()

    print(f"   📊 Found: {journals_count} journal entries, {journal_images_count} journal images")

    if journals_count == 0 and journal_images_count == 0:
        print("   ✅ No journal data to delete")
        return

    try:
        # Delete journal images first
        if user_id:
            deleted_journal_images = db.session.query(DailyJournalImage).filter_by(user_id=user_id).delete()
        else:
            deleted_journal_images = db.session.query(DailyJournalImage).delete()
        print(f"   🗑️  Deleted {deleted_journal_images} journal images")

        # Delete journal entries
        if user_id:
            deleted_journals = db.session.query(DailyJournal).filter_by(user_id=user_id).delete()
        else:
            deleted_journals = db.session.query(DailyJournal).delete()
        print(f"   🗑️  Deleted {deleted_journals} journal entries")

        db.session.commit()
        print("   ✅ Journal data deletion completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error deleting journal data: {e}")
        raise


def delete_user_tags(user_id=None):
    """Delete user-created tags, preserving default tags."""

    print("\n🗑️  Deleting user-created tags...")

    try:
        # Count tags
        if user_id:
            user_tags_count = Tag.query.filter_by(user_id=user_id, is_default=False).count()
            default_tags_count = Tag.query.filter_by(is_default=True).count()
        else:
            user_tags_count = Tag.query.filter_by(is_default=False).count()
            default_tags_count = Tag.query.filter_by(is_default=True).count()

        print(f"   📊 Found: {user_tags_count} user tags, {default_tags_count} default tags")

        if user_tags_count == 0:
            print("   ✅ No user tags to delete")
            return

        # Delete only user-created tags (not default tags)
        if user_id:
            deleted_tags = db.session.query(Tag).filter_by(user_id=user_id, is_default=False).delete()
        else:
            deleted_tags = db.session.query(Tag).filter_by(is_default=False).delete()

        print(f"   🗑️  Deleted {deleted_tags} user-created tags")
        print(f"   ✅ Preserved {default_tags_count} default tags")

        db.session.commit()
        print("   ✅ Tag cleanup completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error deleting tags: {e}")
        raise


def delete_instruments():
    """Delete all instruments (optional)."""

    print("\n🗑️  Deleting instruments...")

    instruments_count = Instrument.query.count()
    print(f"   📊 Found: {instruments_count} instruments")

    if instruments_count == 0:
        print("   ✅ No instruments to delete")
        return

    try:
        deleted_instruments = db.session.query(Instrument).delete()
        print(f"   🗑️  Deleted {deleted_instruments} instruments")

        db.session.commit()
        print("   ✅ Instruments deletion completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error deleting instruments: {e}")
        raise


def cleanup_test_data(user_id=None, include_instruments=False):
    """Main cleanup function."""

    print(f"\n🧹 STARTING TEST DATA CLEANUP")
    print("=" * 50)

    if user_id:
        print(f"👤 Targeting User ID: {user_id}")
    else:
        print("🌐 Targeting ALL USERS")

    try:
        # Delete in proper order to respect foreign key constraints

        # 1. Delete trade-related data first (has foreign keys to models)
        delete_trade_related_data(user_id)

        # 2. Delete trading models
        delete_trading_models(user_id)

        # 3. Delete journal data
        delete_journal_data(user_id)

        # 4. Delete user tags (preserve defaults)
        delete_user_tags(user_id)

        # 5. Delete instruments (optional)
        if include_instruments:
            delete_instruments()

        print(f"\n🎉 CLEANUP COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("✅ All test data has been removed")
        print("✅ Default tags preserved")
        print("✅ User accounts preserved")
        print("✅ System data preserved")

        if not include_instruments:
            print("ℹ️  Instruments were preserved (use --instruments flag to remove)")

    except Exception as e:
        print(f"\n❌ CLEANUP FAILED: {e}")
        print("🔄 Database has been rolled back")
        raise


def show_current_data_summary(user_id=None):
    """Show summary of current data before cleanup."""

    print(f"\n📊 CURRENT DATA SUMMARY")
    print("=" * 30)

    try:
        if user_id:
            trades = Trade.query.filter_by(user_id=user_id).count()
            models = TradingModel.query.filter_by(user_id=user_id).count()
            journals = DailyJournal.query.filter_by(user_id=user_id).count()
            user_tags = Tag.query.filter_by(user_id=user_id, is_default=False).count()
        else:
            trades = Trade.query.count()
            models = TradingModel.query.count()
            journals = DailyJournal.query.count()
            user_tags = Tag.query.filter_by(is_default=False).count()

        default_tags = Tag.query.filter_by(is_default=True).count()
        instruments = Instrument.query.count()

        print(f"📈 Trades: {trades}")
        print(f"🎯 Trading Models: {models}")
        print(f"📖 Journal Entries: {journals}")
        print(f"🏷️  User Tags: {user_tags}")
        print(f"🏷️  Default Tags: {default_tags}")
        print(f"📊 Instruments: {instruments}")

    except Exception as e:
        print(f"❌ Error getting data summary: {e}")


def main():
    """Main execution function."""

    print("🧹 TEST DATA CLEANUP SCRIPT")
    print("=" * 50)
    print("This script removes all generated test data while preserving:")
    print("• Default system tags")
    print("• User accounts")
    print("• System configuration")
    print("=" * 50)

    # Parse command line arguments
    import sys
    include_instruments = '--instruments' in sys.argv
    target_user = None

    # Look for --user=X argument
    for arg in sys.argv:
        if arg.startswith('--user='):
            try:
                target_user = int(arg.split('=')[1])
                print(f"👤 Targeting specific user: {target_user}")
            except ValueError:
                print("❌ Invalid user ID. Use --user=1 format.")
                return

    # Initialize Flask app
    app = create_app()

    with app.app_context():
        print("\n🔧 Connecting to database...")

        # Show current data summary
        show_current_data_summary(target_user)

        # Get confirmation
        if not confirm_deletion():
            return

        print(f"\n⏰ Starting cleanup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            cleanup_test_data(target_user, include_instruments)

            # Show final summary
            print(f"\n📊 FINAL DATA SUMMARY")
            print("=" * 30)
            show_current_data_summary(target_user)

        except Exception as e:
            print(f"\n💥 FATAL ERROR: {e}")
            print("🔧 Please check the database and try again")


if __name__ == "__main__":
    main()