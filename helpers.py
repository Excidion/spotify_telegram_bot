import country_converter as coco
import requests
from staticmap import StaticMap, Line
import logging
from io import BytesIO
from haversine import haversine, Unit
import pytz
from datetime import datetime, timedelta
from random import randrange

logger = logging.getLogger(__name__)

man_emojis = ["\U0001F468", "\U0001F9D4", "\U0001F9D4", "\U0000200D", "\U00002642", "\U0000FE0F", "\U0001F468", "\U0000200D", "\U0001F9B0",
              "\U0001F468", "\U0000200D", "\U0001F9B1", "\U0001F468", "\U0000200D", "\U0001F9B3", "\U0001F468", "\U0000200D", "\U0001F9B2", "\U0001F474"]

woman_emojis = ["\U0001F469	", "\U0001F469", "\U0000200D", "\U0001F9B0", "\U0001F469", "\U0000200D", "\U0001F9B1",
                "\U0001F469", "\U0000200D", "\U0001F9B3", "\U0001F471", "\U0000200D", "\U00002640", "\U0000FE0F", "\U0001F475"]

excuse_array = ["I met a really nice goat",
                "I just came accross a fruit tree",
                "I lost data connection",
                "I met a super nice man " +
                man_emojis[randrange(len(man_emojis))],
                "I met a super nice woman " +
                woman_emojis[randrange(len(woman_emojis))],
                "I met some really nice people ",
                "I just got into an accident \U0001F62E	(hopefully not. Send me more songs to find out if I am still alive \U0001F601)"]

going_fast_array = [""]

going_slow_array = [""]

going_normal_array = [""]


def degree_to_text(degree):
    if degree > 337.5:
        return 'North'
    if degree > 292.5:
        return 'North West'
    if degree > 247.5:
        return 'West'
    if degree > 202.5:
        return 'South West'
    if degree > 157.5:
        return 'South'
    if degree > 122.5:
        return 'South East'
    if degree > 67.5:
        return 'East'
    if degree > 22.5:
        return 'North East'
    return 'North'


def get_weather_text(API_KEY, current_lat, current_lon):
    base_url = 'http://api.openweathermap.org/data/2.5/weather?'
    payload = {
        'lat': current_lat,
        'lon': current_lon,
        'units': 'metric',
        'APPID': API_KEY
    }
    json_data = requests.get(base_url, params=payload).json()
    logger.info(
        "Weather data received.")
    weather_data = json_data["weather"][0]
    # icon_url = "http://openweathermap.org/img/w/" z+ weather_data.icon + ".png";
    converter = coco.CountryConverter()
    country = converter.convert(
        json_data["sys"]["country"], src='ISO2', to='name_short')
    weather_text = "I am in {} right now. It is {}°C and we have {}. The wind speed is {}m/s going {}.".format(
        country, int(json_data["main"]["temp"]), weather_data["description"], int(json_data["wind"]["speed"]), degree_to_text(json_data["wind"]["deg"]))
    return country, weather_text


def transform(locations):
    result = []
    for location in locations:
        result.append([location["lon"], location["lat"]])
    return result


def draw_map(location_entry):
    m = StaticMap(400, 400, 80)
    locations = location_entry["locations"]
    coordinates = transform(locations)
    line_outline = Line(coordinates, 'white', 4)
    line = Line(coordinates, '#D2322D', 3)

    m.add_line(line_outline)
    m.add_line(line)
    image = m.render()
    byte_io = BytesIO()

    image.save(byte_io, 'PNG')
    #image.save(str(location_entry["message_id"]) + '.png')
    return byte_io.getvalue()


def prepare_listened_length_message(locations_during_song, last_song_length, datetime_format):
    last_song_length_time = timedelta(milliseconds=last_song_length)
    length_listened = datetime.now(
        pytz.utc) - datetime.strptime(locations_during_song[0]["time"], datetime_format)
    listened_info = "I listened to your song for {}. ".format(
        length_listened)
    if last_song_length_time - length_listened > timedelta(seconds=20):
        listened_info += "Seems like I didn't listen to the whole song since the song you sent me is actually {} long. A possible explanation is that I didn't like it. But that is not the only possibility! Maybe I couldn't keep listening to it because {}. I am just saying, let's not jump to conclusions. ".format(
            last_song_length_time, excuse_array[randrange(len(excuse_array))])
    elif last_song_length_time - length_listened > timedelta(seconds=0):
        listened_info += "Seems like I liked your song, since I listened to the whole thing. "
    else:
        listened_info += "I must have paused your song in the middle for a while since your song is only {} long. ".format(
            last_song_length_time)
    return listened_info, length_listened


def prepare_distance_traveled_message(distance, length_listened, speed_during_song):
    distance_info = "Your song has accompanied me for a total distance of {}km! Thank you so much. While listening to your song I had an average speed of {}km/h. ".format(
        distance, speed_during_song)
    if speed_during_song > 20:
        distance_info += "Wow, I went super fast during your song! Either I went downhill, had really strong backwind, or your song gave me a boost of energy. "
    elif speed_during_song > 15:
        distance_info += "I had a really nice cruising speed while listening to your song."
    else:
        distance_info += "Man, I went kind of slow during your song. But oh well. It's not all about speed right? Maybe I went so slow because I stopped at a fruit tree or met some nice people."
    return distance_info


def calculate_distance(locations_during_song):
    distance_traveled = 0
    for x in range(len(locations_during_song) - 1):
        loc1 = (locations_during_song[x]["lat"],
                locations_during_song[x]["lon"])
        loc2 = (locations_during_song[x + 1]["lat"],
                locations_during_song[x + 1]["lon"])
        distance_traveled += haversine(loc1, loc2, unit=Unit.KILOMETERS)
    return round(distance_traveled, 2)
