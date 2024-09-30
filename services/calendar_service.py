import datetime
import pandas_market_calendars as mcal


def get_0dte_expiration_date():
    # Get the current date
    current_date = datetime.datetime.now().date()

    # Get the NYSE calendar
    nyse = mcal.get_calendar("NYSE")

    # Get the valid trading days from today onwards
    valid_days = nyse.valid_days(
        start_date=current_date, end_date=current_date + datetime.timedelta(days=365)
    )

    # Find the closest valid trading day that isn't a bank holiday
    expiration_date = None
    for day in valid_days:
        if day.date() >= current_date:
            expiration_date = day.date().strftime("%Y%m%d")
            break

    if expiration_date is None:
        raise ValueError("No valid expiration date found within the next year.")

    return expiration_date
