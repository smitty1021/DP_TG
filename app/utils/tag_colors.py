"""
Tag color mapping based on Random's performance-based system
"""


def get_tag_color_class(tag_name):
    """
    Returns CSS class for tag coloring based on Random's methodology

    GREEN (GOOD Performance) Tags:
    - Quality execution and discipline

    BLUE (NEUTRAL/Informational) Tags:
    - Setup/Strategy identification
    - Market classification and analysis

    RED (BAD Performance) Tags:
    - Poor execution and discipline issues
    """

    # GREEN (GOOD Performance) Tags
    good_performance_tags = {
        "Front Run", "Confirmation", "Retest", "Proper Stop",
        "Let Run", "Partial Profit", "Disciplined", "Patient",
        "Calm", "Confident", "Followed Plan"
    }

    # RED (BAD Performance) Tags
    bad_performance_tags = {
        "Chased Entry", "Late Entry", "Moved Stop", "Cut Short",
        "FOMO", "Revenge Trading", "Impulsive", "Anxious",
        "Broke Rules", "Overconfident"
    }

    # All others are BLUE (NEUTRAL/Informational)
    # This includes all setup/strategy, classification, and session tags

    if tag_name in good_performance_tags:
        return "tag-good"  # Green
    elif tag_name in bad_performance_tags:
        return "tag-bad"  # Red
    else:
        return "tag-neutral"  # Blue