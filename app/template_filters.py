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


def register_template_filters(app):
    """Register custom template filters"""
    app.jinja_env.filters['tag_color'] = get_tag_color_class