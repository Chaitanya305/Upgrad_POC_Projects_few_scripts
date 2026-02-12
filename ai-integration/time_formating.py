from datetime import datetime, timezone, timedelta

def time_formating(start_time_value, duration ):

    timestamp_ms = start_time_value # Start time in milliseconds
    duration_ms = duration  # Duration in milliseconds

    timestamp_sec = timestamp_ms / 1000
    duration_sec = duration_ms / 1000

    # Convert to UTC time
    start_time = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)

    # If duration is less than 6 minute, set end time to 6 minutes from start
    if duration_sec < 360:
        end_time = start_time + timedelta(minutes=6)
    else:
        end_time = start_time + timedelta(seconds=duration_sec)

    # Format times in required format
    formatted_start_time = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    formatted_end_time = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    formatted_date = start_time.strftime("%Y.%m.%d")

    return formatted_start_time, formatted_end_time, formatted_date
