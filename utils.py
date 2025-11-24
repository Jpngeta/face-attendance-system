"""
Utility functions for the Flask application
"""
import pytz
from datetime import datetime
from flask import current_app

def convert_utc_to_local(utc_datetime):
    """
    Convert UTC datetime to local timezone
    
    Args:
        utc_datetime: datetime object (assumed to be UTC if no timezone)
    
    Returns:
        datetime object in local timezone
    """
    if utc_datetime is None:
        return None
    
    # If datetime has no timezone info, assume it's UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)
    
    # Get configured timezone
    tz_name = current_app.config.get('TIMEZONE', 'UTC')
    tz = pytz.timezone(tz_name)
    
    # Convert to local timezone
    return utc_datetime.astimezone(tz)