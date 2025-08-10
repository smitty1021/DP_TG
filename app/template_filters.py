def get_tag_color_class(tag_or_name):
    """Template filter for tag color classes - accepts Tag object or tag name"""

    # If it's a Tag object, check if it has a color_category set
    if hasattr(tag_or_name, 'color_category') and tag_or_name.color_category:
        return f"tag-{tag_or_name.color_category}"

    # Fall back to name-based logic for backward compatibility
    tag_name = tag_or_name.name if hasattr(tag_or_name, 'name') else str(tag_or_name)

    good_performance_tags = {
        "Front Run", "Confirmation", "Retest", "Proper Stop",
        "Let Run", "Partial Profit", "Disciplined", "Patient",
        "Calm", "Confident", "Followed Plan"
    }

    bad_performance_tags = {
        "Chased Entry", "Late Entry", "Moved Stop", "Cut Short",
        "FOMO", "Revenge Trading", "Impulsive", "Anxious",
        "Broke Rules", "Overconfident"
    }

    if tag_name in good_performance_tags:
        return "tag-good"
    elif tag_name in bad_performance_tags:
        return "tag-bad"
    else:
        return "tag-neutral"


def eastern_time_filter(utc_datetime):
    """Convert UTC datetime to Eastern time with proper EST/EDT handling"""
    from datetime import timezone, timedelta
    import pytz
    
    if not utc_datetime:
        return 'Never'
    
    try:
        # Ensure the datetime is timezone-aware (UTC)
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        
        # Convert to Eastern timezone
        eastern_tz = pytz.timezone('US/Eastern')
        eastern_time = utc_datetime.astimezone(eastern_tz)
        
        # Format as "DD MMM YY HH:MM EST/EDT"
        # pytz automatically handles EST/EDT based on the date
        return eastern_time.strftime('%d %b %y %H:%M %Z')
        
    except Exception as e:
        # Fallback to original format if conversion fails
        return utc_datetime.strftime('%d %b %y %H:%M UTC') if utc_datetime else 'Never'


def nl2br(text):
    """Convert newlines to HTML line breaks"""
    if not text:
        return text
    from markupsafe import Markup
    return Markup(str(text).replace('\n', '<br>\n'))


def register_template_filters(app):
    """Register custom template filters"""
    app.jinja_env.filters['tag_color'] = get_tag_color_class
    app.jinja_env.filters['eastern_time'] = eastern_time_filter
    app.jinja_env.filters['nl2br'] = nl2br