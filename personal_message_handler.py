import json
import datetime
import pytz


class PersonalMessageHandler:
    def __init__(self):
        self.current_message_index = 0

    def add(self, message_content, uri, first_name, last_name, username, chat_id):
        with open("personal_messages.json") as json_file:
            data = json.load(json_file)
            temp = data["personal_messages"]
            formatted_message = {
                "id": temp[-1]["id"] + 1 if len(temp) > 0 else 0,
                "content": message_content,
                "status": "created",
                "uri": uri,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "chat_id": chat_id,
                "timestamp": datetime.datetime.now(pytz.utc).__str__(),
            }

            temp.append(formatted_message)
        with open("personal_messages.json", "w") as file:
            json.dump(data, file, indent=4)

        return True

    def is_current_message(self, message, uri):
        return message["status"] == "created" and message["uri"] == uri

    def find_message(self, uri):
        with open("personal_messages.json") as json_file:
            data = json.load(json_file)
            message_list = data["personal_messages"]
            matching_message = next(
                (
                    x
                    for x in message_list
                    if (x["status"] == "created" and x["uri"] == uri)
                ),
                None,
            )
            return matching_message

    def mark_message_listened(self, message):
        with open("personal_messages.json", "r") as file:
            data = json.load(file)
        matching_message = next(
            (x for x in data["personal_messages"] if (x == message)), None
        )
        matching_message["status"] = "listened"
        with open("personal_messages.json", "w") as json_file:
            json.dump(data, json_file, indent=4)

    def get_unlistened_messages(self):
        with open("personal_messages.json", "r") as json_file:
            data = json.load(json_file)
            message_list = data["personal_messages"]
            output_dict = [x for x in message_list if x["status"] == "created"]
            return output_dict

    def get_last_added_message(self):
        with open("personal_messages.json", "r") as json_file:
            data = json.load(json_file)
            song_list = data["personal_messages"]
            new_song_dict = song_list[-1]
            return new_song_dict
