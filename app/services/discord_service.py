# Replace your app/services/discord_service.py with this corrected version:

import os
import discord
from discord.ext import commands
import asyncio
import threading
from typing import Optional, List, Dict
import aiohttp
import json
import logging


class DiscordService:
    """Service to handle Discord API interactions."""

    def __init__(self):
        self.bot = None
        self.guild_id = os.getenv('DISCORD_GUILD_ID')
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.client_id = os.getenv('DISCORD_CLIENT_ID')
        self.client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        self._guild = None
        self._ready = False
        self._app = None  # Store Flask app reference
        self.logger = logging.getLogger(__name__)

    def initialize(self, app=None):
        """Initialize Discord bot with Flask app context."""
        from flask import current_app

        # Store the Flask app reference
        if app:
            self._app = app
        else:
            self._app = current_app._get_current_object()

        if not self.bot_token or not self.guild_id:
            self.logger.error("Discord configuration missing. Check DISCORD_BOT_TOKEN and DISCORD_GUILD_ID")
            return False

        try:
            intents = discord.Intents.default()
            intents.guilds = True
            intents.members = True  # Needed to read member roles

            self.bot = discord.Client(intents=intents)

            @self.bot.event
            async def on_ready():
                # Use app context for logging
                with self._app.app_context():
                    self._app.logger.info(f"Discord bot logged in as {self.bot.user}")
                    self._guild = self.bot.get_guild(int(self.guild_id))
                    if self._guild:
                        self._app.logger.info(f"Connected to guild: {self._guild.name}")
                        self._ready = True
                    else:
                        self._app.logger.error(f"Could not find guild with ID: {self.guild_id}")

            # Start bot in background thread with app context
            def run_bot():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.bot.start(self.bot_token))
                except Exception as e:
                    # Use app context for error logging
                    with self._app.app_context():
                        self._app.logger.error(f"Discord bot error: {e}")

            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Discord service: {e}")
            return False

    def is_ready(self) -> bool:
        """Check if Discord service is ready."""
        return self._ready and self.bot and not self.bot.is_closed()

    async def get_user_roles(self, discord_user_id: str) -> List[Dict]:
        """Get roles for a Discord user."""
        if not self.is_ready():
            self.logger.warning("Discord service not ready")
            return []

        try:
            member = self._guild.get_member(int(discord_user_id))
            if not member:
                # Try to fetch member if not in cache
                member = await self._guild.fetch_member(int(discord_user_id))

            if not member:
                self.logger.warning(f"Member {discord_user_id} not found in guild")
                return []

            roles = []
            for role in member.roles:
                if role.name != "@everyone":  # Skip @everyone role
                    roles.append({
                        'id': str(role.id),
                        'name': role.name,
                        'position': role.position,
                        'permissions': [perm.name for perm, value in role.permissions if value]
                    })

            return roles

        except Exception as e:
            self.logger.error(f"Error getting user roles for {discord_user_id}: {e}")
            return []

    def get_user_roles_sync(self, discord_user_id: str) -> List[Dict]:
        """Synchronous wrapper for getting user roles."""
        if not self.is_ready():
            return []

        try:
            # Create new event loop for this thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(self.get_user_roles(discord_user_id))
        except Exception as e:
            self.logger.error(f"Error in sync role fetch: {e}")
            return []

    async def get_guild_roles(self) -> List[Dict]:
        """Get all roles from the Discord guild."""
        if not self.is_ready():
            return []

        try:
            roles = []
            for role in self._guild.roles:
                if role.name != "@everyone":
                    roles.append({
                        'id': str(role.id),
                        'name': role.name,
                        'position': role.position,
                        'member_count': len(role.members),
                        'permissions': [perm.name for perm, value in role.permissions if value]
                    })

            return sorted(roles, key=lambda x: x['position'], reverse=True)

        except Exception as e:
            self.logger.error(f"Error getting guild roles: {e}")
            return []

    def get_guild_roles_sync(self) -> List[Dict]:
        """Synchronous wrapper for getting guild roles."""
        if not self.is_ready():
            return []

        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(self.get_guild_roles())
        except Exception as e:
            self.logger.error(f"Error in sync guild roles fetch: {e}")
            return []

    def get_guild_info(self) -> Dict:
        """Get Discord guild information."""
        if not self.is_ready():
            return {}

        try:
            return {
                'id': str(self._guild.id),
                'name': self._guild.name,
                'member_count': self._guild.member_count,
                'role_count': len(self._guild.roles),
                'description': self._guild.description,
                'icon_url': str(self._guild.icon.url) if self._guild.icon else None
            }
        except Exception as e:
            self.logger.error(f"Error getting guild info: {e}")
            return {}

    def validate_user_in_guild(self, discord_user_id: str) -> bool:
        """Check if user is a member of the Discord guild."""
        if not self.is_ready():
            return False

        try:
            member = self._guild.get_member(int(discord_user_id))
            return member is not None
        except Exception as e:
            self.logger.error(f"Error validating user in guild: {e}")
            return False

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """Exchange OAuth2 code for access token."""
        token_url = "https://discord.com/api/oauth2/token"

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"Token exchange failed: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[Dict]:
        """Get Discord user information using access token."""
        user_url = "https://discord.com/api/users/@me"

        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"User info fetch failed: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None

    def close(self):
        """Close Discord connection."""
        if self.bot and not self.bot.is_closed():
            asyncio.create_task(self.bot.close())


# Global Discord service instance
discord_service = DiscordService()