import time
import psutil
import threading
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text
from app.extensions import db
from app.models import User, Instrument, Tag, P12Scenario


class SystemHealthMonitor:
    """Enterprise-grade system health monitoring."""

    def __init__(self):
        self._last_check = None
        self._cache_duration = timedelta(seconds=30)  # Cache for 30 seconds
        self._cached_status = None
        self._lock = threading.Lock()

    def get_system_status(self):
        """Get comprehensive system status with intelligent caching."""
        with self._lock:
            now = datetime.utcnow()

            # Return cached status if still valid
            if (self._cached_status and self._last_check and
                    now - self._last_check < self._cache_duration):
                return self._cached_status

            # Perform fresh system check
            try:
                status = self._perform_health_check()
                self._cached_status = status
                self._last_check = now
                return status
            except Exception as e:
                current_app.logger.error(f"System health check failed: {e}", exc_info=True)
                return self._get_fallback_status()

    def _perform_health_check(self):
        """Perform comprehensive system health assessment."""
        status = {
            'overall_status': 'operational',
            'components': {},
            'metrics': {},
            'last_updated': datetime.utcnow().isoformat()
        }

        # 1. Database Health Check
        db_status = self._check_database_health()
        status['components']['database'] = db_status

        # 2. Application Health Check
        app_status = self._check_application_health()
        status['components']['application'] = app_status

        # 3. P12 Engine Status
        p12_status = self._check_p12_engine_status()
        status['components']['p12_engine'] = p12_status

        # 4. Analytics Engine Status (Simulated)
        analytics_status = self._check_analytics_engine_status()
        status['components']['analytics_engine'] = analytics_status

        # 5. System Metrics
        status['metrics'] = self._collect_system_metrics()

        # 6. Resource Utilization
        status['resources'] = self._calculate_resource_utilization()

        # Determine overall system status
        status['overall_status'] = self._calculate_overall_status(status['components'])

        return status

    def _check_database_health(self):
        """Check database connection and performance."""
        try:
            start_time = time.time()

            # Test basic connectivity
            result = db.session.execute(text("SELECT 1")).scalar()
            if result != 1:
                raise Exception("Database connectivity test failed")

            # Test query performance
            query_time = time.time() - start_time

            # Get connection pool status
            engine = db.engine
            pool = engine.pool

            return {
                'status': 'operational',
                'response_time_ms': round(query_time * 1000, 2),
                'connection_pool_size': pool.size(),
                'checked_out_connections': pool.checkedout(),
                'checked_in_connections': pool.checkedin(),
                'details': 'Database connectivity verified'
            }

        except Exception as e:
            current_app.logger.error(f"Database health check failed: {e}")
            return {
                'status': 'error',
                'response_time_ms': None,
                'error': str(e),
                'details': 'Database connection failed'
            }

    def _check_application_health(self):
        """Check Flask application health."""
        try:
            # Check if we can access current_app
            app_name = current_app.name
            debug_mode = current_app.debug

            # Get system uptime (simplified)
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            return {
                'status': 'operational',
                'app_name': app_name,
                'debug_mode': debug_mode,
                'uptime_hours': round(uptime.total_seconds() / 3600, 1),
                'details': 'Application running normally'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': 'Application health check failed'
            }

    def _check_p12_engine_status(self):
        """Check P12 scenario engine status."""
        try:
            # Count active P12 scenarios
            active_scenarios = P12Scenario.query.filter_by(is_active=True).count()
            total_scenarios = P12Scenario.query.count()

            # Get recent usage (last 24 hours)
            from app.models import P12UsageStats
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_usage = P12UsageStats.query.filter(
                P12UsageStats.selection_timestamp >= yesterday
            ).count()

            status = 'operational' if active_scenarios > 0 else 'maintenance'

            return {
                'status': status,
                'active_scenarios': active_scenarios,
                'total_scenarios': total_scenarios,
                'recent_usage_24h': recent_usage,
                'details': f'{active_scenarios} scenarios active'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'details': 'P12 engine check failed'
            }

    def _check_analytics_engine_status(self):
        """Check analytics engine status (simulated for now)."""
        # Since analytics engine is in development, return maintenance status
        return {
            'status': 'maintenance',
            'deployment_status': 'scheduled',
            'details': 'Scheduled Deployment - Q2 2025',
            'estimated_completion': '2025-04-15'
        }

    def _collect_system_metrics(self):
        """Collect key system performance metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_usage_percent': round(cpu_percent, 1),
                'memory_usage_percent': round(memory.percent, 1),
                'memory_available_gb': round(memory.available / (1024 ** 3), 2),
                'disk_usage_percent': round(disk.percent, 1),
                'disk_free_gb': round(disk.free / (1024 ** 3), 2)
            }

        except Exception as e:
            return {
                'error': str(e),
                'cpu_usage_percent': None,
                'memory_usage_percent': None
            }

    def _calculate_resource_utilization(self):
        """Calculate resource utilization percentages for the dashboard."""
        try:
            # Active vs Total Instruments
            active_instruments = Instrument.query.filter_by(is_active=True).count()
            total_instruments = Instrument.query.count()

            # Active vs Total Tags
            active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
            total_tags = Tag.query.filter_by(is_default=True).count()

            # Active vs Total Users (capacity planning)
            total_users = User.query.filter_by(is_active=True).count()
            user_capacity_limit = 100  # Configurable limit

            return {
                'instruments': {
                    'active': active_instruments,
                    'total': total_instruments,
                    'percentage': round((active_instruments / max(total_instruments, 1)) * 100, 1)
                },
                'tags': {
                    'active': active_tags,
                    'total': total_tags,
                    'percentage': round((active_tags / max(total_tags, 1)) * 100, 1)
                },
                'users': {
                    'current': total_users,
                    'capacity': user_capacity_limit,
                    'percentage': round((total_users / user_capacity_limit) * 100, 1)
                }
            }

        except Exception as e:
            current_app.logger.error(f"Resource utilization calculation failed: {e}")
            return {
                'instruments': {'active': 0, 'total': 0, 'percentage': 0},
                'tags': {'active': 0, 'total': 0, 'percentage': 0},
                'users': {'current': 0, 'capacity': 100, 'percentage': 0}
            }

    def _calculate_overall_status(self, components):
        """Calculate overall system status based on component statuses."""
        statuses = [comp.get('status', 'unknown') for comp in components.values()]

        if 'error' in statuses:
            return 'degraded'
        elif 'maintenance' in statuses:
            return 'maintenance'
        elif all(status == 'operational' for status in statuses):
            return 'operational'
        else:
            return 'degraded'

    def _get_fallback_status(self):
        """Return fallback status when health check fails."""
        return {
            'overall_status': 'unknown',
            'components': {
                'database': {'status': 'unknown', 'details': 'Health check failed'},
                'application': {'status': 'unknown', 'details': 'Health check failed'},
                'p12_engine': {'status': 'unknown', 'details': 'Health check failed'},
                'analytics_engine': {'status': 'maintenance', 'details': 'Scheduled Deployment'}
            },
            'metrics': {},
            'resources': {
                'instruments': {'active': 0, 'total': 0, 'percentage': 0},
                'tags': {'active': 0, 'total': 0, 'percentage': 0},
                'users': {'current': 0, 'capacity': 100, 'percentage': 0}
            },
            'last_updated': datetime.utcnow().isoformat()
        }


# Global instance
system_monitor = SystemHealthMonitor()


def get_system_health():
    """Convenience function to get system health status."""
    return system_monitor.get_system_status()


# ================================
# Status Display Helpers
# ================================

def format_status_display(status_key, component_data):
    """Format status for display in the dashboard."""
    status = component_data.get('status', 'unknown')

    status_mapping = {
        'operational': {
            'class': 'status-operational',
            'icon': 'fas fa-check-circle',
            'label': 'Operational'
        },
        'maintenance': {
            'class': 'status-maintenance',
            'icon': 'fas fa-tools',
            'label': 'Maintenance'
        },
        'error': {
            'class': 'status-error',
            'icon': 'fas fa-exclamation-triangle',
            'label': 'Error'
        },
        'degraded': {
            'class': 'status-degraded',
            'icon': 'fas fa-exclamation-circle',
            'label': 'Degraded'
        },
        'unknown': {
            'class': 'status-error',
            'icon': 'fas fa-question-circle',
            'label': 'Unknown'
        }
    }

    return status_mapping.get(status, status_mapping['unknown'])


def get_status_trend_indicator(current_value, threshold_good=80, threshold_warning=60):
    """Get trend indicator class based on value thresholds."""
    if current_value >= threshold_good:
        return 'trend-indicator positive'
    elif current_value >= threshold_warning:
        return 'trend-indicator'
    else:
        return 'trend-indicator negative'