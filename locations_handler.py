import json
import datetime
import pytz
import logging

logger = logging.getLogger(__name__)


class LocationsHandler:
    def __init__(self):
        self.current_message_index = 0

    def add(self, locations, message_id, chat_id, username, first_name, last_name, distance, speed, duration_listened, country):
        with open('locations.json') as json_file:
            data = json.load(json_file)
            temp = data['locations']
            formatted_message = {"id": temp[-1]["id"] + 1 if len(temp) > 0 else 0,
                                 "locations": locations,
                                 "message_id": message_id,
                                 "from_chat_id": chat_id,
                                 "from_username": username,
                                 "from_first_name": first_name,
                                 "from_last_name": last_name,
                                 "distance": distance,
                                 "average_speed": speed,
                                 "duration_listened_sec": duration_listened,
                                 "country": country,
                                 "timestamp": datetime.datetime.now(pytz.utc).__str__()}

            temp.append(formatted_message)
        with open('locations.json', "w") as file:
            json.dump(data, file, indent=4)
        logger.info("Location for message with ID {} successfully saved.".format(
            message_id))
        return True

    def get_all_locations(self):
        with open('locations.json') as json_file:
            data = json.load(json_file)
            location_list = data['locations']
        logger.info("{} locations successfully retrieved.".format(
            len(location_list)))
        return location_list

    def find_locations(self, message_id):
        location_list = self.get_all_locations()
        matching_location_entry = next((x for x in location_list if (
            x["message_id"] == message_id)), None)
        logger.info(
            "Matching location entry with message_id {} retrieved.".format(message_id))
        return matching_location_entry

    def get_locations_by_user(self, location_list, chat_id):
        output_dict = [
            x for x in location_list if x["from_chat_id"] == chat_id]
        logger.info("{} locations retrieved for user with chat_id {}.".format(
            len(output_dict), chat_id))
        return output_dict

    def get_locations_by_users(self):
        location_list = self.get_all_locations()
        # get unique chat_ids
        values = set()
        for item in location_list:
            values.add(item['from_chat_id'])
        logger.info("A total of {} users have sent songs.".format(len(values)))
        locations_by_users = {}
        for item in values:
            locations_by_users[item] = self.get_locations_by_user(
                location_list, item)
        return locations_by_users

    def detailed_stats(self, user_locations):
        if user_locations == None:
            return None
        total_listen_time = 0
        distance = 0
        countries = set()
        for location in user_locations:
            distance += location["distance"]
            total_listen_time += location["duration_listened_sec"]
            countries.add(location["country"])
        average_speed = round(distance / (total_listen_time / 3600), 2)
        time_listened_min = int(total_listen_time / 60)
        return {"distance": round(distance, 2), "average_speed": average_speed, "time_listened_min": time_listened_min, "countries": countries}

    def add_up_distance(self, user_locations):
        total_distance = 0
        chat_id = user_locations[0]["from_chat_id"]
        first_name = ""
        last_name = ""
        username = ""
        for location in user_locations:
            if location["from_first_name"]:
                first_name = location["from_first_name"]
            if location["from_last_name"]:
                last_name = location["from_last_name"]
            if location["from_username"]:
                username = location["from_username"]
            total_distance += location["distance"]

        if last_name and first_name:
            user = first_name + " " + last_name
        elif first_name:
            user = first_name
        elif last_name:
            user = last_name
        else:
            user = chat_id
        return {"user": user, "total_distance": round(total_distance, 2), "chat_id": chat_id}

    def build_leaderboard(self, chat_id):
        users_locations = self.get_locations_by_users()
        user_stats = self.detailed_stats(users_locations.get(int(chat_id)))
        leaderboard = []
        ranks_above = ""
        motivation_text = ""
        for user in users_locations:
            leaderboard.append(self.add_up_distance(users_locations[user]))
        leaderboard.sort(key=lambda x: x["total_distance"], reverse=True)
        entry_to_find = next(
            (x for x in leaderboard if (x["chat_id"] == int(chat_id))), None)
        if entry_to_find != None:
            matching_rank_entry = leaderboard.index(entry_to_find) + 1
            your_rank_text = "You have already accompanied me on {}km in {} {} ({}) with your music! That ranks you place {} on my top DJ list. I have listened to the songs you sent me for a total of {} {}. So my average speed during that time was {}km/h!\n\n".format(
                user_stats["distance"], len(user_stats["countries"]), "country" if len(user_stats["countries"]) == 1 else "countries", ', '.join(user_stats["countries"]), matching_rank_entry, user_stats["time_listened_min"], "minute" if user_stats["time_listened_min"] == 1 else "minutes", user_stats["average_speed"])
            if matching_rank_entry == 1:
                motivation_text = "You are my favorite DJ at the moment! \U0001F947 Thank you for your most appreciated support \U0001F618. \n\n"
            else:
                difference_to_above = leaderboard[matching_rank_entry -
                                                  2]["total_distance"] - entry_to_find["total_distance"]
                motivation_text = "The person a rank above you accompanied me by {}km more than you. Let's close that gap and make YOU my top DJ! \U0001F4BF \n\n".format(
                    difference_to_above)
            if matching_rank_entry > 10:

                rank = matching_rank_entry - 6
                for score in leaderboard[matching_rank_entry - 6:matching_rank_entry]:
                    ranks_above += str(rank) + ". " + \
                        str(score[0]) + " - " + str(score[1]) + "km \n"
                    rank += 1
        else:
            your_rank_text = "I have not listened to any songs sent by you yet. I am therefore not able to give you your rank.\U0001F625 \n\n"

        if len(leaderboard) > 0:
            leaderboard_text = "My top 10 DJs: \n"
        else:
            leaderboard_text = "I have not been sent any songs yet and can therefore not show you a leaderboard.\U0001F625 \n"
        rank = 1
        for score in leaderboard[:10]:
            leaderboard_text += str(rank) + ". " + \
                str(score["user"]) + " - " + \
                str(score["total_distance"]) + "km \n"
            rank += 1
        return your_rank_text + motivation_text + leaderboard_text + ranks_above
