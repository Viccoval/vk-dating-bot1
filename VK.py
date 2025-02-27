
import requests
import configparser
import vk_api


from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType

#Конфигурация
config = configparser.ConfigParser()
config.read('Settings.ini')
vk_token = config['Tokens']['vk_token_gr']
vk_token_id = config['Tokens']['vk_token_id']
user_id = config['User_id']['id']



# Авторизация в вк
vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()

longpoll = VkLongPoll(vk_session)

class VK_get:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {
            'access_token': access_token,
            'v': version
        }

    def get_user_info(self, user_id, fields='bdate,sex,city'):                  # Получить информацию о пользователе, который обющается с ботом
        url = f'{self.base_address}users.get'
        params = {
            'user_ids': user_id,
            'fields': fields
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()


class VK_get_id:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {
            'access_token': access_token,
            'v': version
        }

    def search_by_users(self, sex, city, age_from, age_to):                      # Поиск по параметрам
        url = f'{self.base_address}users.search'
        params = {
            'sex': sex,      # 1-women, 2-men, 0-default
            'city': city,
            'age_from': age_from,
            'age_to': age_to,
            'count': 100,
            'sort': 1
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()


    def get_photos(self, user_id):                                               # Получить фото
        url = f'{self.base_address}photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'count': 3
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()


class Work_with_users(VK_get_id):
    def __init__(self, access_token, version='5.199'):
        super().__init__(access_token, version)

    def get_users_photo(self, sex, city, age_from, age_to, user_id):                 # Получить популярные фото
        search_results = self.search_by_users(sex, city, age_from, age_to)

        if 'response' in search_results and search_results['response']['count'] > 0:
            users = search_results['response']['items']
            if 'response' in search_results and search_results['response']['count'] > 0:
                users = search_results['response']['items']
                for user in users:
                    user_id = user['id']
                    name = user['first_name']
                    last_name = user['last_name']
                    profile_url = f'https://vk.com/id{user_id}'

                    if user.get('is_closed', False):
                        print(f"Профиль пользователя {name} {last_name} закрыт.")
                        continue

                    photos = self.get_photos(user_id)
                    if 'response' in photos and isinstance(photos['response'], list) and len(photos['response']) > 0:
                        attachments = []
                        for photo in photos['response'][:3]:
                            attachments.append(f'photo{photo["owner_id"]}_{photo["id"]}')

                        message_text = f"Имя и фамилия: {name} {last_name}\nСсылка на профиль: {profile_url}"

                        write_msg(user_id, message_text)

                        # vk.messages.send(
                        #     peer_id=peer_id,
                        #     message=message_text,
                        #     attachment=','.join(attachments),
                        #     random_id=randrange(10**7)
                        # )

                    else:
                        print(f"Нет доступных фотографий для пользователя {user_id}.")
            else:
                print("Нет пользователей, подходящих под критерии поиска.")



def write_msg(user_id, message):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=randrange(10 ** 7)
    )

def listen_for_messages():
    for event in longpoll.listen():

        if event.type == VkEventType.MESSAGE_NEW:

            if event.to_me:
                request = event.text
                user_id = event.user_id

                if request == "привет":
                    write_msg(event.user_id, f"Хай, {event.user_id}")
                elif request == "пока":
                    write_msg(event.user_id, "Пока((")
                else:
                    write_msg(event.user_id, "Не поняла вашего ответа...")



if __name__ == "__main__":
    listen_for_messages()
    user_id = user_id


# vk_get = VK_get(vk_token)
# user_info = vk_get.get_user_info(user_id, fields='bdate,sex,city')
# print(user_info)
#
# vk_get_id = VK_get_id(vk_token_id)
# search_results = vk_get_id.search_by_users(sex=1, city=1, age_from=18, age_to=35)
#
# pprint(search_results)
#
#
# work = Work_with_users(vk_token_id)
# work.get_users_photo(sex=1, city=2, age_from=18, age_to=30, peer_id = user_id)

