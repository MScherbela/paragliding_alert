import json
import datetime
import dateutil
from dataclasses import dataclass
import requests
import logging
from enum import IntEnum
from utils import remove_short_windows
import os

@dataclass
class WeatherData:
    time: datetime.datetime  # local time in Vienna
    wind: float  # km/h
    gust: float  # km/h
    temp: float  # deg C
    prec: float  # precipitation in mm/h
    wind_dir: float  # degrees


class WeatherStatus(IntEnum):
    NO = 0
    MAYBE = 1
    YES = 2


def parse_weather_data(fname):
    with open(fname) as f:
        data = json.load(f)

    model = 'sg'
    local_tz = dateutil.tz.gettz("Europe/Vienna")
    utc_tc = dateutil.tz.tzutc()

    parsed_data = []
    for d in data['hours']:
        t = datetime.datetime.fromisoformat(d['time'])
        t = t.replace(tzinfo=utc_tc).astimezone(local_tz).replace(tzinfo=None)
        parsed_data.append(WeatherData(time=t,
                                       wind=d['windSpeed'][model] * 3.6,
                                       gust=d['gust'][model] * 3.6,
                                       temp=d['airTemperature'][model],
                                       prec=d['precipitation'][model],
                                       wind_dir=d['windDirection'][model],
                                       ))
    return parsed_data


def is_flyable(weather: WeatherData, config):
    if weather.gust >= config.max_gust:
        return WeatherStatus.NO
    if weather.wind >= config.max_wind:
        return WeatherStatus.NO
    if weather.prec >= config.max_prec:
        return WeatherStatus.NO

    t = weather.time.time()
    if weather.time.weekday() in [5,6]:
        # Saturday, Sunday
        if (t < config.start_time_weekend) or (t > config.end_time):
            return WeatherStatus.NO
    elif weather.time.weekday() == 4:
        # Friday
        if (t < config.start_time_friday) or (t > config.end_time):
            return WeatherStatus.NO
    else:
        # Mon - Thursday
        if (t < config.start_time_weekday) or (t > config.end_time):
            return WeatherStatus.NO
    if (weather.gust <= config.max_gust/2) and (weather.wind <= config.max_wind/2) and (weather.prec <= config.max_prec/2):
        return WeatherStatus.YES
    else:
        return WeatherStatus.MAYBE


def get_daily_flight_status(times, flight_status, min_window):
    is_maybe = remove_short_windows([s >= WeatherStatus.MAYBE for s in flight_status], min_window)
    is_good = remove_short_windows([s >= WeatherStatus.YES for s in flight_status], min_window)

    status = []
    days = []
    ind_start = 0
    day = datetime.datetime(year=times[0].year, month=times[0].month, day=times[0].day)
    while day < times[-1]:
        duration = 24 - times[ind_start].hour
        if any(is_good[ind_start:ind_start+duration]):
            status.append(2)
        elif any(is_maybe[ind_start:ind_start+duration]):
            status.append(1)
        else:
            status.append(0)
        days.append(day)
        ind_start += duration
        day = day + datetime.timedelta(days=1)
    return days, status


def get_daytimes(t_min, t_max, morning=7, night=20):
    WEEKDAY_VALUES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    mornings = []
    nights = []
    is_weekend = []
    weekdays = []
    day_start = datetime.datetime(year=t_min.year, month=t_min.month, day=t_min.day)
    while day_start < t_max:
        mornings.append(day_start + datetime.timedelta(hours=morning))
        nights.append(day_start + datetime.timedelta(hours=night))
        is_weekend.append(day_start.weekday() in [5,6])
        weekdays.append(WEEKDAY_VALUES[day_start.weekday()%7])
        day_start = day_start + datetime.timedelta(hours=24)
    return mornings, nights, is_weekend, weekdays

def get_weather_fname(id):
    return f"/data/weather_location_{id}.json"


def retrieve_weather_data(lat, lon, fname, api_key=None):
    api_key = api_key or os.environ['WEATHER_API_KEY']
    headers = dict(Authorization=api_key)
    WEATHER_PARAMS = "airTemperature,airTemperature800hpa,cloudCover,precipitation,visibility,gust,windDirection,windDirection100m,windDirection800hpa,windSpeed,windSpeed800hpa"
    params = dict(lat=lat, lng=lon, params=WEATHER_PARAMS)
    response = requests.get("https://api.stormglass.io/v2/weather/point", params=params, headers=headers)
    if response.status_code == 200:
        with open(fname, 'w') as f:
            f.write(response.text)
        return True
    else:
        logging.error(f"Could not retrieve weather data: Status Code: {response.status_code}")
        logging.error(response.text)
        return False

