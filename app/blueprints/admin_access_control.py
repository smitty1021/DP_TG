# app/blueprints/admin_access_control.py
"""
Administrative Access Control System
Manages Discord role-based page access permissions
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from collections import defaultdict
from datetime import datetime
import json

from app.extensions import db
from app.models import DiscordRolePermission, User, PageAccessPermission, AccessControlGroup, UserAccessLog, \
    RolePermissionTemplate
from app.blueprints.admin_bp import admin_required

# Try to import discord service - handle gracefully if not available
# Temporarily disable Discord service for testing
try:
    from app.services.discord_service import discord_service
    DISCORD_SERVICE_AVAILABLE = True
except ImportError:
    DISCORD_SERVICE_AVAILABLE = False
    discord_service = None
    current_app.logger.warning("Discord service not available for access control")

access_control_bp = Blueprint('access_control', __name__, url_prefix='/admin/access-control')


class PageAccessManager:
    """Manages page access permissions and Discord role mappings."""

    def __init__(self):
        self.load_page_definitions()

    def load_page_definitions(self):
        """Load all available pages and their routes from the Flask app."""
        self.pages = {}
        self.page_groups = {}

        # Get all routes from Flask
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint and not rule.endpoint.startswith('static'):
                # Parse route information
                page_info = self._parse_route(rule)
                if page_info:
                    self.pages[rule.endpoint] = page_info

        # Define logical page groups
        self._define_page_groups()

    def _parse_route(self, rule):
        """Parse a Flask route into page information."""
        try:
            # Skip certain system routes
            skip_endpoints = [
                'admin.debug_',
                'auth.discord_callback',
                'auth.discord_sync',
                '.static',
                '_debug_toolbar'
            ]

            if any(skip in rule.endpoint for skip in skip_endpoints):
                return None

            # Extract blueprint and function name
            parts = rule.endpoint.split('.')
            blueprint = parts[0] if len(parts) > 1 else 'main'
            function_name = parts[-1]

            # Generate user-friendly names
            display_name = self._generate_display_name(function_name, blueprint)
            category = self._categorize_page(blueprint, function_name)

            return {
                'endpoint': rule.endpoint,
                'url_rule': rule.rule,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                'blueprint': blueprint,
                'function_name': function_name,
                'display_name': display_name,
                'category': category,
                'requires_auth': True,
                'admin_only': 'admin' in function_name.lower() or blueprint == 'admin'
            }
        except Exception as e:
            current_app.logger.warning(f"Error parsing route {rule.endpoint}: {e}")
            return None

    def _generate_display_name(self, function_name, blueprint):
        """Generate user-friendly display names for pages."""
        # Custom mappings for better names
        name_mappings = {
            'index': 'Dashboard',
            'portfolio_analytics': 'Portfolio Analytics',
            'view_trades_list': 'Trades Management',
            'admin_dashboard': 'Administration Center',
            'admin_users_list': 'User Management',
            'instruments_list': 'Instruments Configuration',
            'manage_default_tags': 'Tags Configuration',
            'user_profile': 'User Profile',
            'daily_journal_list': 'Daily Journal',
            'view_trading_models_list': 'Trading Models',
            'user_my_files': 'Document Repository'
        }

        if function_name in name_mappings:
            return name_mappings[function_name]

        # Generate from function name
        name = function_name.replace('_', ' ').title()

        # Add blueprint context if helpful
        if blueprint != 'main':
            name = f"{blueprint.title()} - {name}"

        return name

    def _categorize_page(self, blueprint, function_name):
        """Categorize pages into logical groups."""
        category_mappings = {
            'admin': 'Administration',
            'auth': 'Authentication',
            'main': 'Core Features',
            'trades': 'Trading Operations',
            'analytics': 'Business Intelligence',
            'files': 'Document Management',
            'images': 'Media Management',
            'trading_models': 'Strategy Management',
            'journals': 'Journal System',
            'p12_scenarios': 'P12 Scenarios'
        }

        return category_mappings.get(blueprint, 'Miscellaneous')

    def _define_page_groups(self):
        """Define logical groups of pages for bulk permission management."""
        # Get all non-admin pages
        non_admin_pages = [ep for ep, info in self.pages.items() if not info['admin_only']]

        self.page_groups = {
            'administration': {
                'name': 'Administration',
                'description': 'Complete access to all functions including administrative controls',
                'pages': [ep for ep, info in self.pages.items()]  # All pages
            },
            'pack_member': {
                'name': 'Pack Member',
                'description': 'Full access except administrative functions',
                'pages': non_admin_pages
            },
            'squad_leader': {
                'name': 'Squad Leader',
                'description': 'Full access except administrative functions',
                'pages': non_admin_pages
            },
            'team_leader_lvl_3': {
                'name': 'Team Leader Lvl III',
                'description': 'Advanced access - TBD based on requirements',
                'pages': [ep for ep, info in self.pages.items()
                          if info['blueprint'] in ['main', 'trades', 'trading_models', 'analytics', 'journals']]
            },
            'team_leader_lvl_2': {
                'name': 'Team Leader Lvl II',
                'description': 'Intermediate access - TBD based on requirements',
                'pages': [ep for ep, info in self.pages.items()
                          if info['blueprint'] in ['main', 'trades', 'trading_models', 'journals']]
            },
            'team_leader_lvl_1': {
                'name': 'Team Leader Lvl I',
                'description': 'Basic leadership access - TBD based on requirements',
                'pages': [ep for ep, info in self.pages.items()
                          if info['blueprint'] in ['main', 'trades', 'journals']]
            }
        }

    def get_pages_by_category(self):
        """Get pages organized by category."""
        categories = defaultdict(list)
        for endpoint, info in self.pages.items():
            categories[info['category']].append({
                'endpoint': endpoint,
                'display_name': info['display_name'],
                'url_rule': info['url_rule'],
                'admin_only': info['admin_only']
            })
        return dict(categories)

    def get_available_groups(self):
        """Get available page groups for bulk assignment."""
        return self.page_groups


@access_control_bp.route('/')
@login_required
@admin_required
def access_control_dashboard():
    """Main access control management dashboard."""
    manager = PageAccessManager()

    # Get current Discord roles - handle case where service isn't available
    discord_roles = []
    if DISCORD_SERVICE_AVAILABLE:
        try:
            # Try different methods that might exist in your Discord service
            if hasattr(discord_service, 'get_all_server_roles'):
                discord_roles = discord_service.get_all_server_roles()
            elif hasattr(discord_service, 'get_guild_roles'):
                discord_roles = discord_service.get_guild_roles()
            else:
                # Fallback - create empty list with a note
                discord_roles = []
                flash('Discord roles feature not yet configured.', 'info')
        except Exception as e:
            current_app.logger.error(f"Error fetching Discord roles: {e}")
            flash('Warning: Could not fetch Discord roles. Discord service may not be configured.', 'warning')
    else:
        discord_roles = [
            {'id': 'mock_admin', 'name': 'Admin', 'member_count': 5},
            {'id': 'mock_premium', 'name': 'Premium Member', 'member_count': 25},
            {'id': 'mock_student1', 'name': 'Student Tier 1', 'member_count': 100},
            {'id': 'mock_student2', 'name': 'Student Tier 2', 'member_count': 50},
            {'id': 'mock_basic', 'name': 'Basic User', 'member_count': 200}
        ]

    # Get existing role permissions and filter out any with invalid access_level values
    try:
        existing_permissions = DiscordRolePermission.query.all()
        # Filter out any permissions with invalid access_level values
        valid_permissions = []
        for perm in existing_permissions:
            if perm.access_level and perm.access_level in ['basic', 'premium', 'vip', 'admin']:
                valid_permissions.append(perm)
            else:
                # Fix invalid access_level values
                current_app.logger.warning(f"Fixing invalid access_level for role {perm.discord_role_id}")
                perm.access_level = 'basic'
                db.session.add(perm)
        
        db.session.commit()
        permissions_by_role = {perm.discord_role_id: perm for perm in valid_permissions}
    except Exception as e:
        current_app.logger.error(f"Error loading role permissions: {e}")
        permissions_by_role = {}

    # Get pages by category
    pages_by_category = manager.get_pages_by_category()

    # Get available groups
    available_groups = manager.get_available_groups()

    return render_template('admin/access_control/dashboard.html',
                           title='Access Control Management',
                           discord_roles=discord_roles,
                           pages_by_category=pages_by_category,
                           available_groups=available_groups,
                           permissions_by_role=permissions_by_role)


@access_control_bp.route('/roles/refresh', methods=['POST'])
@login_required
@admin_required
def refresh_discord_roles():
    """Refresh Discord roles from the server."""
    if not DISCORD_SERVICE_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Discord service not available'
        }), 500

    try:
        if hasattr(discord_service, 'get_all_server_roles'):
            discord_roles = discord_service.get_all_server_roles()
        elif hasattr(discord_service, 'get_guild_roles'):
            discord_roles = discord_service.get_guild_roles()
        else:
            discord_roles = []

        return jsonify({
            'success': True,
            'message': f'Successfully fetched {len(discord_roles)} Discord roles',
            'roles': discord_roles
        })
    except Exception as e:
        current_app.logger.error(f"Error refreshing Discord roles: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to refresh Discord roles: {str(e)}'
        }), 500


@access_control_bp.route('/permissions/save', methods=['POST'])
@login_required
@admin_required
def save_role_permissions():
    """Save role permissions configuration."""
    try:
        data = request.get_json()
        role_id = data.get('role_id')
        role_name = data.get('role_name')
        permissions = data.get('permissions', {})

        if not role_id or not role_name:
            return jsonify({
                'success': False,
                'message': 'Role ID and name are required'
            }), 400

        # Get or create role permission record
        role_permission = DiscordRolePermission.query.filter_by(
            discord_role_id=role_id
        ).first()

        if not role_permission:
            role_permission = DiscordRolePermission(
                discord_role_id=role_id,
                discord_role_name=role_name,
                access_level='basic'  # Ensure a valid default value
            )
            db.session.add(role_permission)
        else:
            role_permission.discord_role_name = role_name

        # Update permissions - ensure access_level is valid
        access_level = permissions.get('access_level', 'basic')
        if not access_level or access_level not in ['basic', 'premium', 'vip', 'admin']:
            access_level = 'basic'
        role_permission.access_level = access_level
        role_permission.can_access_portfolio = permissions.get('can_access_portfolio', False)
        role_permission.can_access_backtesting = permissions.get('can_access_backtesting', False)
        role_permission.can_access_live_trading = permissions.get('can_access_live_trading', False)
        role_permission.can_access_analytics = permissions.get('can_access_analytics', False)
        role_permission.can_access_advanced_features = permissions.get('can_access_advanced_features', False)

        # Save page-specific permissions
        page_permissions = permissions.get('pages', [])
        role_permission.custom_permissions = {
            'allowed_pages': page_permissions,
            'updated_by': current_user.username,
            'updated_at': datetime.utcnow().isoformat()
        }

        db.session.commit()

        # Log the activity
        current_app.logger.info(
            f"Admin {current_user.username} updated permissions for Discord role {role_name} ({role_id})"
        )

        return jsonify({
            'success': True,
            'message': f'Permissions updated for role "{role_name}"'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving role permissions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to save permissions: {str(e)}'
        }), 500


@access_control_bp.route('/groups/apply', methods=['POST'])
@login_required
@admin_required
def apply_group_permissions():
    """Apply a predefined group of permissions to a role."""
    try:
        data = request.get_json()
        role_id = data.get('role_id')
        group_key = data.get('group_key')

        if not role_id or not group_key:
            return jsonify({
                'success': False,
                'message': 'Role ID and group key are required'
            }), 400

        manager = PageAccessManager()
        groups = manager.get_available_groups()

        if group_key not in groups:
            return jsonify({
                'success': False,
                'message': f'Invalid group key: {group_key}'
            }), 400

        group = groups[group_key]

        # Get the role permission record
        role_permission = DiscordRolePermission.query.filter_by(
            discord_role_id=role_id
        ).first()

        if not role_permission:
            return jsonify({
                'success': False,
                'message': 'Role permission record not found. Please save basic permissions first.'
            }), 404

        # Update custom permissions with group pages
        current_permissions = role_permission.custom_permissions or {}
        current_permissions['allowed_pages'] = group['pages']
        current_permissions['applied_group'] = group_key
        current_permissions['group_applied_by'] = current_user.username
        current_permissions['group_applied_at'] = datetime.utcnow().isoformat()

        role_permission.custom_permissions = current_permissions
        db.session.commit()

        current_app.logger.info(
            f"Admin {current_user.username} applied group '{group_key}' to role {role_permission.discord_role_name}"
        )

        return jsonify({
            'success': True,
            'message': f'Applied "{group["name"]}" permissions to role',
            'pages': group['pages']
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error applying group permissions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to apply group permissions: {str(e)}'
        }), 500


@access_control_bp.route('/permissions/<role_id>')
@login_required
@admin_required
def get_role_permissions(role_id):
    """Get current permissions for a specific role."""
    try:
        role_permission = DiscordRolePermission.query.filter_by(
            discord_role_id=role_id
        ).first()

        if not role_permission:
            return jsonify({
                'success': True,
                'permissions': None
            })

        permissions = {
            'access_level': role_permission.access_level,
            'can_access_portfolio': role_permission.can_access_portfolio,
            'can_access_backtesting': role_permission.can_access_backtesting,
            'can_access_live_trading': role_permission.can_access_live_trading,
            'can_access_analytics': role_permission.can_access_analytics,
            'can_access_advanced_features': role_permission.can_access_advanced_features,
            'custom_permissions': role_permission.custom_permissions
        }

        return jsonify({
            'success': True,
            'permissions': permissions
        })

    except Exception as e:
        current_app.logger.error(f"Error getting role permissions: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get permissions: {str(e)}'
        }), 500


@access_control_bp.route('/test/page-access/<role_id>')
@login_required
@admin_required
def test_role_access(role_id):
    """Test what pages a specific Discord role can access."""
    try:
        # Get role permissions
        role_permission = DiscordRolePermission.query.filter_by(
            discord_role_id=role_id
        ).first()

        if not role_permission:
            return jsonify({
                'success': False,
                'message': 'No permissions configured for this role'
            })

        # Get allowed pages
        custom_permissions = role_permission.custom_permissions or {}
        allowed_pages = custom_permissions.get('allowed_pages', [])

        # Get page manager for display names
        manager = PageAccessManager()

        # Build accessible pages list
        accessible_pages = []
        for page_endpoint in allowed_pages:
            if page_endpoint in manager.pages:
                page_info = manager.pages[page_endpoint]
                accessible_pages.append({
                    'endpoint': page_endpoint,
                    'display_name': page_info['display_name'],
                    'category': page_info['category'],
                    'url_rule': page_info['url_rule']
                })

        return jsonify({
            'success': True,
            'role_name': role_permission.discord_role_name,
            'access_level': role_permission.access_level,
            'accessible_pages': accessible_pages,
            'total_pages': len(accessible_pages)
        })

    except Exception as e:
        current_app.logger.error(f"Error testing role access: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to test role access: {str(e)}'
        }), 500


@access_control_bp.route('/users/inactive', methods=['POST'])
@login_required
@admin_required
def deactivate_users_without_roles():
    """Deactivate users who no longer have valid Discord roles."""
    try:
        # Find users with Discord accounts
        discord_users = User.query.filter(
            User.discord_linked == True,
            User.discord_id.isnot(None),
            User.is_active == True
        ).all()

        deactivated_count = 0
        errors = []

        for user in discord_users:
            try:
                # Skip admin users
                if user.is_admin():
                    continue

                # Check if user still has valid roles
                if user.discord_roles:
                    role_ids = [role['id'] for role in user.discord_roles]
                    valid_permissions = DiscordRolePermission.query.filter(
                        DiscordRolePermission.discord_role_id.in_(role_ids)
                    ).first()

                    # If no valid permissions found, deactivate
                    if not valid_permissions:
                        user.is_active = False
                        deactivated_count += 1
                        current_app.logger.info(f"Deactivated user {user.username} - no valid Discord roles")
                else:
                    # No Discord roles at all, deactivate
                    user.is_active = False
                    deactivated_count += 1
                    current_app.logger.info(f"Deactivated user {user.username} - no Discord roles")

            except Exception as e:
                errors.append(f"Error processing user {user.username}: {str(e)}")

        db.session.commit()

        message = f"Deactivated {deactivated_count} users without valid Discord roles"
        if errors:
            message += f". {len(errors)} errors occurred."

        return jsonify({
            'success': True,
            'message': message,
            'deactivated_count': deactivated_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating users: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to deactivate users: {str(e)}'
        }), 500