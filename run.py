import os
from app import create_app, db # Import db if you plan to add CLI commands that use it
import click
# from app.models import User, TradingModel # etc. - Import models if needed for CLI commands

# Create the Flask app instance using the app factory
# The FLASK_CONFIG environment variable can be used to specify
# 'development', 'testing', 'production' if you set up config classes.
# For now, it will use the defaults in create_app().
config_name = os.getenv('FLASK_CONFIG', 'default')
app = create_app() # You can pass config_name if you set up different configs

# --- Optional: Add Flask CLI Commands ---
# (Useful for database operations, creating admin users, etc.)

@app.shell_context_processor
def make_shell_context():
    """Makes db and models available in 'flask shell'."""
    # Ensure all models you want in the shell are imported in app.models
    from app import models
    return {'db': db, 'User': models.User, 'TradingModel': models.TradingModel,
            'Trade': models.Trade, 'DailyJournal': models.DailyJournal,
            'Instrument': models.Instrument,  # ADD THIS LINE
            # Add other models here as needed
           }

@app.cli.command("init-db")
def init_db_command():
    """Clears existing data and creates new tables (for development)."""
    click.confirm("This will delete all existing data. Do you want to continue?", abort=True)
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database and dropped all existing data.")
    # You could call a function here to seed initial data if desired
    # E.g., from app.models import seed_initial_data; seed_initial_data()
    # The initial data setup in app/__init__.py will run on app creation context.


@app.cli.command("seed-instruments")
def seed_instruments_command():
    """Seed default instruments if none exist."""
    import click
    from app.models import Instrument
    from datetime import datetime

    if Instrument.query.count() > 0:
        click.echo("Instruments already exist. Skipping seed.")
        return

    # UPDATED instruments with correct symbols
    instruments_data = [
        {
            'symbol': 'NQ', 'name': 'E-mini NASDAQ-100', 'exchange': 'CME',
            'asset_class': 'Equity Index', 'product_group': 'E-mini Futures',
            'point_value': 5.0, 'tick_size': 0.25, 'currency': 'USD'
        },
        {
            'symbol': 'ES', 'name': 'E-mini S&P 500', 'exchange': 'CME',
            'asset_class': 'Equity Index', 'product_group': 'E-mini Futures',
            'point_value': 12.5, 'tick_size': 0.25, 'currency': 'USD'
        },
        {
            'symbol': 'YM', 'name': 'E-mini Dow Jones', 'exchange': 'CME',
            'asset_class': 'Equity Index', 'product_group': 'E-mini Futures',
            'point_value': 5.0, 'tick_size': 1.0, 'currency': 'USD'
        }
    ]

    for data in instruments_data:
        instrument = Instrument(**data)
        db.session.add(instrument)

    db.session.commit()
    click.echo(f"Created {len(instruments_data)} default instruments.")

# Example: Command to create a default admin user (if not already present)
#@app.cli.command("create-admin")
#@click.argument("username")
#@click.argument("email")
#@click.argument("password")
#def create_admin_command(username, email, password):
#    from app.models import User, UserRole
#    if User.find_by_username(username) or User.find_by_email(email):
#        click.echo("Admin user with that username or email already exists.")
#        return
#   admin = User(username=username, email=email, role=UserRole.ADMIN, is_email_verified=True, is_active=True)
#    admin.set_password(admin123)
#    db.session.add(admin)
#    db.session.commit()
#    click.echo(f"Admin user {username} created.")

if __name__ == '__main__':
    # The FLASK_DEBUG environment variable will be used if set.
    # Otherwise, debug=True here will enable it.
    # For production, ensure debug is False.
    app.run(debug=(os.environ.get('FLASK_DEBUG', '1') == '1'))


# Or you can add the command directly here:
@app.cli.command("migrate-p12-images")
def migrate_p12_images_command():
    """Migrate existing P12 scenario images to global system."""
    import click
    from app.utils.p12_image_helpers import migrate_legacy_p12_images

    click.echo("Starting P12 image migration...")
    result = migrate_legacy_p12_images()

    if result['success']:
        click.echo(f"Migration completed successfully!")
        click.echo(f"Migrated: {result['migrated_count']} images")
        click.echo(f"Total scenarios checked: {result['total_scenarios']}")

        if result['errors']:
            click.echo(f"Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                click.echo(f"  - {error}")
    else:
        click.echo(f"Migration failed: {result['error']}")

# You can then run this command with:
# flask migrate-p12-images