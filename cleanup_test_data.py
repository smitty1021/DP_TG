#!/usr/bin/env python3
"""
Enhanced Test Data Cleanup Script
=================================
Two modes of operation:

1. STANDARD MODE (default): Removes test data while preserving system essentials
   - Preserves admin user and core system data
   - Removes all test users and their data
   - Preserves default tags and system configurations

2. COMPLETE MODE (--complete flag): Nuclear option - deletes EVERYTHING
   - Removes ALL users including admin
   - Removes ALL data from database
   - Leaves completely empty database

Usage:
  python cleanup_test_data.py              # Standard cleanup
  python cleanup_test_data.py --complete   # Complete wipe
  python cleanup_test_data.py --user=123   # Clean specific user only
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

# Import ALL models for complete inventory
from app.models import (
    # Core models
    User, UserRole, Group, PasswordReset, ApiKey,
    # Trading models
    Trade, EntryPoint, ExitPoint, TradingModel, Instrument, Tag, TagCategory,
    # Journal models
    DailyJournal, WeeklyJournal,
    # P12 models
    P12Scenario, P12UsageStats,
    # Image and file models
    TradeImage, DailyJournalImage, GlobalImage, File,
    # Settings
    Settings, AccountSetting, NewsEventItem,
    # Activity
    Activity
)


def confirm_deletion(mode='standard'):
    """Get user confirmation before proceeding with deletion."""

    if mode == 'complete':
        print("🚨 CRITICAL WARNING: COMPLETE DATABASE WIPE")
        print("=" * 60)
        print("This will permanently delete EVERYTHING:")
        print("• ALL users (including admin)")
        print("• ALL data in the entire database")
        print("• You'll need to run create_default_data.py afterwards")
        print("=" * 60)

        confirm1 = input("Delete EVERYTHING including admin user? (yes/no): ").strip().lower()
        if confirm1 != 'yes':
            print("❌ Operation cancelled.")
            return False

        confirm2 = input("Type 'WIPE_EVERYTHING' to confirm complete database wipe: ").strip()
        if confirm2 != 'WIPE_EVERYTHING':
            print("❌ Operation cancelled.")
            return False

        return True

    else:
        print("⚠️  WARNING: STANDARD DATA CLEANUP")
        print("=" * 50)
        print("This script will permanently delete:")
        print("• All test users (testuser1-testuser100)")
        print("• All trades and related data")
        print("• All user-created trading models")
        print("• All journal entries")
        print("• All user-created tags")
        print("• All files and activities")
        print("")
        print("This will preserve:")
        print("• Admin user account")
        print("• Default system tags")
        print("• Default trading models")
        print("• Instruments and P12 scenarios")
        print("• Core system configuration")
        print("=" * 50)

        confirm1 = input("Are you sure you want to clean test data? (yes/no): ").strip().lower()
        if confirm1 != 'yes':
            print("❌ Operation cancelled.")
            return False

        confirm2 = input("This action cannot be undone. Type 'DELETE' to confirm: ").strip()
        if confirm2 != 'DELETE':
            print("❌ Operation cancelled.")
            return False

        return True


def show_data_summary(user_id=None, mode='standard'):
    """Show summary of data that will be affected."""

    print(f"\n📊 DATABASE INVENTORY ({mode.upper()} MODE)")
    print("=" * 50)

    try:
        if mode == 'complete':
            # Show everything
            data_counts = {
                'Users': User.query.count(),
                'Groups': Group.query.count(),
                'Password Resets': PasswordReset.query.count(),
                'API Keys': ApiKey.query.count(),
                'Trades': Trade.query.count(),
                'Entry Points': EntryPoint.query.count(),
                'Exit Points': ExitPoint.query.count(),
                'Trading Models': TradingModel.query.count(),
                'Instruments': Instrument.query.count(),
                'Tags': Tag.query.count(),
                'Daily Journals': DailyJournal.query.count(),
                'Weekly Journals': WeeklyJournal.query.count(),
                'P12 Scenarios': P12Scenario.query.count(),
                'P12 Usage Stats': P12UsageStats.query.count(),
                'Trade Images': TradeImage.query.count(),
                'Daily Journal Images': DailyJournalImage.query.count(),
                'Global Images': GlobalImage.query.count(),
                'Files': File.query.count(),
                'Settings': Settings.query.count(),
                'Account Settings': AccountSetting.query.count(),
                'News Events': NewsEventItem.query.count(),
                'Activities': Activity.query.count()
            }

            total_records = sum(data_counts.values())
            print(f"🚨 EVERYTHING WILL BE DELETED:")

            for entity, count in data_counts.items():
                if count > 0:
                    print(f"   • {entity}: {count:,}")

            print(f"\n💀 TOTAL RECORDS TO DELETE: {total_records:,}")

        else:
            # Standard mode - show what will be preserved vs deleted
            if user_id:
                # Specific user cleanup
                user = User.query.get(user_id)
                if not user:
                    print(f"❌ User ID {user_id} not found")
                    return False

                print(f"👤 CLEANING DATA FOR USER: {user.username} (ID: {user_id})")
                trades_count = Trade.query.filter_by(user_id=user_id).count()
                models_count = TradingModel.query.filter_by(user_id=user_id, is_default=False).count()
                journals_count = DailyJournal.query.filter_by(user_id=user_id).count()
                tags_count = Tag.query.filter_by(user_id=user_id, is_default=False).count()

                print(f"   📈 Trades: {trades_count}")
                print(f"   🎯 User Models: {models_count}")
                print(f"   📖 Journal Entries: {journals_count}")
                print(f"   🏷️  User Tags: {tags_count}")

            else:
                # All test data cleanup
                admin_count = User.query.filter_by(username='admin').count()
                test_users_count = User.query.filter(User.username.like('testuser%')).count()
                total_users = User.query.count()

                trades_count = Trade.query.count()
                user_models_count = TradingModel.query.filter_by(is_default=False).count()
                default_models_count = TradingModel.query.filter_by(is_default=True).count()
                journals_count = DailyJournal.query.count()
                user_tags_count = Tag.query.filter_by(is_default=False).count()
                default_tags_count = Tag.query.filter_by(is_default=True).count()

                print(f"🗑️  TO BE DELETED:")
                print(f"   • Test Users: {test_users_count}")
                print(f"   • All Trades: {trades_count}")
                print(f"   • User Models: {user_models_count}")
                print(f"   • All Journals: {journals_count}")
                print(f"   • User Tags: {user_tags_count}")

                print(f"\n✅ TO BE PRESERVED:")
                print(f"   • Admin Users: {admin_count}")
                print(f"   • Default Models: {default_models_count}")
                print(f"   • Default Tags: {default_tags_count}")
                print(f"   • Instruments: {Instrument.query.count()}")
                print(f"   • P12 Scenarios: {P12Scenario.query.count()}")

        return True

    except Exception as e:
        print(f"❌ Error getting data summary: {e}")
        return True


def delete_complete_database():
    """Nuclear option - delete everything."""

    print(f"\n💥 EXECUTING COMPLETE DATABASE WIPE")
    print("=" * 50)

    # Define deletion order to respect foreign key constraints
    deletion_steps = [
        ("P12 Usage Statistics", P12UsageStats),
        ("Trade Images", TradeImage),
        ("Daily Journal Images", DailyJournalImage),
        ("Global Images", GlobalImage),
        ("Files", File),
        ("Activities", Activity),
        ("Password Resets", PasswordReset),
        ("API Keys", ApiKey),
        ("Entry Points", EntryPoint),
        ("Exit Points", ExitPoint),
        ("Trades", Trade),
        ("Trading Models", TradingModel),
        ("Daily Journals", DailyJournal),
        ("Weekly Journals", WeeklyJournal),
        ("Tags", Tag),
        ("P12 Scenarios", P12Scenario),
        ("Instruments", Instrument),
        ("News Events", NewsEventItem),
        ("Account Settings", AccountSetting),
        ("Settings", Settings),
        ("User Groups", None),  # Special case for associations
        ("Groups", Group),
        ("Users", User),
    ]

    total_deleted = 0

    try:
        for step_name, model_class in deletion_steps:
            print(f"\n🗑️  {step_name}...")

            if model_class is None:
                # Clear user-group associations
                try:
                    from app.models import user_group_association
                    deleted = db.session.execute(user_group_association.delete()).rowcount
                    print(f"   🗑️  Cleared {deleted} associations")
                    total_deleted += deleted
                except Exception as e:
                    print(f"   ⚠️  Could not clear associations: {e}")
                continue

            try:
                count = model_class.query.count()
                if count == 0:
                    print(f"   ✅ No {step_name.lower()} found")
                    continue

                deleted = db.session.query(model_class).delete()
                print(f"   🗑️  Deleted {deleted:,} {step_name.lower()}")
                total_deleted += deleted

                db.session.commit()
                print(f"   ✅ {step_name} completed")

            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Error with {step_name}: {e}")
                continue

        print(f"\n🎉 COMPLETE WIPE SUCCESSFUL!")
        print(f"✅ Total deleted: {total_deleted:,} records")
        print(f"💡 Run create_default_data.py to rebuild system")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ COMPLETE WIPE FAILED: {e}")
        raise


def delete_test_data_standard(user_id=None):
    """Standard cleanup - preserves admin and system data."""

    print(f"\n🧹 STANDARD TEST DATA CLEANUP")
    print("=" * 50)

    if user_id:
        print(f"👤 Targeting User ID: {user_id}")
    else:
        print("🌐 Cleaning ALL test data")

    try:
        # Step 1: Delete user-specific data
        if user_id:
            delete_user_data(user_id)
        else:
            delete_all_test_users_data()

        # Step 2: Clean up orphaned records
        cleanup_orphaned_data()

        print(f"\n🎉 STANDARD CLEANUP COMPLETED!")
        print("=" * 50)
        print("✅ Test data removed")
        print("✅ Admin and system data preserved")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ STANDARD CLEANUP FAILED: {e}")
        raise


def delete_user_data(user_id):
    """Delete all data for a specific user."""

    user = User.query.get(user_id)
    if not user:
        print(f"❌ User ID {user_id} not found")
        return

    print(f"\n🗑️  Deleting data for user: {user.username}")

    # Delete in order of dependencies
    deletion_order = [
        ("Trade Images", lambda: TradeImage.query.filter_by(user_id=user_id).delete()),
        ("Journal Images", lambda: DailyJournalImage.query.filter_by(user_id=user_id).delete()),
        ("P12 Usage Stats", lambda: P12UsageStats.query.filter_by(user_id=user_id).delete()),
        ("Activities", lambda: Activity.query.filter_by(user_id=user_id).delete()),
        ("Files", lambda: File.query.filter_by(user_id=user_id).delete()),
        ("Entry Points", lambda: db.session.query(EntryPoint).join(Trade).filter(Trade.user_id == user_id).delete(
            synchronize_session=False)),
        ("Exit Points", lambda: db.session.query(ExitPoint).join(Trade).filter(Trade.user_id == user_id).delete(
            synchronize_session=False)),
        ("Trades", lambda: Trade.query.filter_by(user_id=user_id).delete()),
        ("Daily Journals", lambda: DailyJournal.query.filter_by(user_id=user_id).delete()),
        ("Weekly Journals", lambda: WeeklyJournal.query.filter_by(user_id=user_id).delete()),
        ("User Trading Models", lambda: TradingModel.query.filter_by(user_id=user_id, is_default=False).delete()),
        ("User Tags", lambda: Tag.query.filter_by(user_id=user_id, is_default=False).delete()),
        ("Settings", lambda: Settings.query.filter_by(user_id=user_id).delete()),
        ("API Keys", lambda: ApiKey.query.filter_by(user_id=user_id).delete()),
        ("Password Resets", lambda: PasswordReset.query.filter_by(user_id=user_id).delete()),
    ]

    for step_name, delete_func in deletion_order:
        try:
            deleted = delete_func()
            if deleted > 0:
                print(f"   🗑️  {step_name}: {deleted}")
        except Exception as e:
            print(f"   ❌ Error with {step_name}: {e}")

    # Finally delete the user (if not admin)
    if user.username != 'admin':
        db.session.delete(user)
        print(f"   🗑️  User Account: {user.username}")

    db.session.commit()
    print(f"   ✅ User cleanup completed")


def delete_all_test_users_data():
    """Delete all test users and their data."""

    print(f"\n🗑️  Deleting ALL test users and data...")

    # Get all test users (excluding admin)
    test_users = User.query.filter(
        User.username != 'admin',
        User.username.like('testuser%')
    ).all()

    print(f"   📊 Found {len(test_users)} test users")

    # Delete each test user's data
    for user in test_users:
        delete_user_data(user.id)

    # Clean up any remaining non-admin, non-default data
    cleanup_remaining_test_data()


def cleanup_remaining_test_data():
    """Clean up any remaining test data not tied to specific users."""

    print(f"\n🧹 Cleaning up remaining test data...")

    try:
        # Delete non-default trading models not owned by admin
        admin_user = User.query.filter_by(username='admin').first()
        admin_id = admin_user.id if admin_user else None

        non_default_models = TradingModel.query.filter(
            TradingModel.is_default == False,
            TradingModel.user_id != admin_id if admin_id else True
        ).delete()

        if non_default_models > 0:
            print(f"   🗑️  Non-default models: {non_default_models}")

        # Delete any orphaned entries/exits
        orphaned_entries = db.session.query(EntryPoint).filter(
            ~EntryPoint.trade_id.in_(db.session.query(Trade.id))
        ).delete(synchronize_session=False)

        orphaned_exits = db.session.query(ExitPoint).filter(
            ~ExitPoint.trade_id.in_(db.session.query(Trade.id))
        ).delete(synchronize_session=False)

        if orphaned_entries > 0:
            print(f"   🗑️  Orphaned entries: {orphaned_entries}")
        if orphaned_exits > 0:
            print(f"   🗑️  Orphaned exits: {orphaned_exits}")

        db.session.commit()
        print(f"   ✅ Remaining cleanup completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error in remaining cleanup: {e}")


def cleanup_orphaned_data():
    """Clean up any orphaned records after user deletion."""

    print(f"\n🧹 Cleaning orphaned data...")

    try:
        # Find and delete orphaned images
        orphaned_trade_images = db.session.query(TradeImage).filter(
            ~TradeImage.user_id.in_(db.session.query(User.id))
        ).delete(synchronize_session=False)

        orphaned_journal_images = db.session.query(DailyJournalImage).filter(
            ~DailyJournalImage.user_id.in_(db.session.query(User.id))
        ).delete(synchronize_session=False)

        orphaned_activities = db.session.query(Activity).filter(
            ~Activity.user_id.in_(db.session.query(User.id))
        ).delete(synchronize_session=False)

        orphaned_files = db.session.query(File).filter(
            ~File.user_id.in_(db.session.query(User.id))
        ).delete(synchronize_session=False)

        if orphaned_trade_images > 0:
            print(f"   🗑️  Orphaned trade images: {orphaned_trade_images}")
        if orphaned_journal_images > 0:
            print(f"   🗑️  Orphaned journal images: {orphaned_journal_images}")
        if orphaned_activities > 0:
            print(f"   🗑️  Orphaned activities: {orphaned_activities}")
        if orphaned_files > 0:
            print(f"   🗑️  Orphaned files: {orphaned_files}")

        db.session.commit()
        print(f"   ✅ Orphaned data cleanup completed")

    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error cleaning orphaned data: {e}")


def main():
    """Main execution function."""

    print("🧹 ENHANCED CLEANUP SCRIPT")
    print("=" * 50)

    # Parse command line arguments
    complete_mode = '--complete' in sys.argv
    target_user = None

    # Look for --user=X argument
    for arg in sys.argv:
        if arg.startswith('--user='):
            try:
                target_user = int(arg.split('=')[1])
                print(f"👤 Targeting specific user: {target_user}")
            except ValueError:
                print("❌ Invalid user ID. Use --user=1 format.")
                return 1

    mode = 'complete' if complete_mode else 'standard'

    if complete_mode:
        print("💀 COMPLETE MODE: Will delete EVERYTHING")
        print("This includes admin users and all system data!")
    else:
        print("🧹 STANDARD MODE: Preserves admin and system data")
        if target_user:
            print(f"Targeting specific user ID: {target_user}")
        else:
            print("Will clean all test users and their data")

    # Initialize Flask app
    app = create_app()

    with app.app_context():
        print("\n🔧 Connecting to database...")

        # Show current data summary
        has_data = show_data_summary(target_user, mode)

        if not has_data and mode != 'complete':
            print("\n✅ No data to clean up!")
            return 0

        # Get confirmation
        if not confirm_deletion(mode):
            return 0

        print(f"\n⏰ Starting cleanup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            if complete_mode:
                delete_complete_database()
            else:
                delete_test_data_standard(target_user)

            # Show final summary
            print(f"\n📊 POST-CLEANUP SUMMARY")
            print("=" * 30)
            show_data_summary(target_user, mode)

            print(f"\n🎉 SUCCESS! Cleanup completed successfully!")

            if complete_mode:
                print(f"💡 Next step: run 'python create_default_data.py'")
            else:
                print(f"✅ Admin user and system data preserved")

        except Exception as e:
            print(f"\n💥 CLEANUP FAILED: {e}")
            print("🔧 Please check the database and try again")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    exit(main())