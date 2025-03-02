import requests
import configparser
import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType

# Импортируем БДшку
from DB_love import session, User, Candidate, Favorite, Blacklist, Viewed, Photo, UserPhotoLike

# ------------------ Конфигурация и авторизация ------------------
config = configparser.ConfigParser()
config.read('Settings.ini')
vk_token = config['Tokens']['vk_token_gr']
vk_token_id = config['Tokens']['vk_token_id']
# Используем ID из конфига для отправки сообщений от имени бота
bot_vk_id = int(config['User_id']['id'])

vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ------------------ Глобальные переменные поиска------------------

user_states = {}          # Состояние пользователя
user_search_params = {}   # Параметры поиска

# ------------------ Работа с БД ------------------

def get_or_create_user(vk_id):
    user = session.query(User).filter_by(vk_id=vk_id).first()
    if not user:
        # Создаем пустого без души как в бличе
        user = User(
            vk_id=vk_id,
            first_name="",
            last_name="",
            age=None,
            gender="",
            city=""
        )
        session.add(user)
        session.commit()
    return user

def process_registration(user_vk_id, text):
    try:
        # Формат: Имя, Фамилия, возраст, пол, город
        parts = [part.strip() for part in text.split(',')]
        if len(parts) != 5:
            raise ValueError("написано мало или много параметров исправляй")
        first_name, last_name, age, gender, city = parts
        try:
          int(age)
        except error:
          write_msg(user_vk_id, "Хватит прикалываться, ну или нужно написать целое число")
        user = session.query(User).filter_by(vk_id=user_vk_id).first()
        user.first_name = first_name
        user.last_name = last_name
        user.age = int(age)
        user.gender = gender
        user.city = city
        session.commit()
        write_msg(user_vk_id, "Так и быть, теперь мы тебя запомнили")
        send_main_menu(user_vk_id)
    except Exception as e:
        write_msg(user_vk_id, f"Ошибочная попытка в: {str(e)}. Попробуй еще раз, только попробуй думать и напиши в формате: Имя, Фамилия, возраст, пол, город")

def get_or_create_candidate(candidate_data):
    vk_candidate_id = candidate_data['id']
    candidate = session.query(Candidate).filter_by(vk_id=vk_candidate_id).first()
    if not candidate:
        candidate = Candidate(
            vk_id=vk_candidate_id,
            first_name=candidate_data.get('first_name', ''),
            last_name=candidate_data.get('last_name', ''),
            profile_link=f"https://vk.com/id{vk_candidate_id}",
            # На случай если из вк ниче не получил
            age=candidate_data.get('age'),
            gender=str(candidate_data.get('sex', '')),
            city=candidate_data.get('city', '')
        )
        session.add(candidate)
        session.commit()
    return candidate

# ------------------ Функция отправки сообщений ------------------
def write_msg(user_id, message):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=randrange(10 ** 7)
    )

# ------------------ Формирования меню ------------------
def send_main_menu(user_id):
    message = ("Главное меню:\n"
               "1. Найти кандидатов\n"
               "2. Мои избранные\n"
               "3. Настройки\n"
               "4. Помощь")
    write_msg(user_id, message)
    user_states[user_id] = "main_menu"

def help_menu(user_id):
    message = ("Помощь:\n"
               "Чтобы начать поиск, выберите 'Найти кандидатов'.\n"
               "В разделе 'Мои избранные' можно просматривать и удалять избранных кандидатов.\n"
               "В 'Настройках' можно изменить параметры поиска.\n"
               "При поиске доступны команды:\n"
               "Лайк, Избранное, Следующий, Черный список")
    write_msg(user_id, message)
    send_main_menu(user_id)

def settings_menu(user_id):
    message = ("Настройки поиска:\n"
               "Введите новые параметры в формате:\n"
               "пол, город, возраст от, возраст до\n"
               "Например: 1, 1, 18, 30")
    write_msg(user_id, message)
    user_states[user_id] = "settings"

def process_settings(user_id, text):
    try:
        parts = [part.strip() for part in text.split(',')]
        if len(parts) != 4:
            raise ValueError("Снова угараешь.")
        sex = int(parts[0])
        city = int(parts[1])
        age_from = int(parts[2])
        age_to = int(parts[3])
        user_search_params[user_id] = {
            'sex': sex,
            'city': city,
            'age_from': age_from,
            'age_to': age_to
        }
        write_msg(user_id, "Ты на карандаше!")
    except Exception as e:
        write_msg(user_id, f"Здесь: {str(e)} Ошибка. Плиз трай эгейн.")
        return
    send_main_menu(user_id)

# ------------------ Работа с кандидатами ------------------
# Здесь можно использовать API VK для поиска кандидатов. Можно сказать как первый код, чутка потправил и проапгрейдил.
class VK_get_id:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {'access_token': access_token, 'v': version}

    def search_by_users(self, sex, city, age_from, age_to):
        url = f'{self.base_address}users.search'
        params = {
            'sex': sex,         # 1 - женщины, 2 - мужчины, 0 - по умолчанию
            'city': city,
            'age_from': age_from,
            'age_to': age_to,
            'count': 100,
            'sort': 1
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()

    def get_photos(self, user_id):
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

    def get_users_photo(self, sex, city, age_from, age_to):
        search_results = self.search_by_users(sex, city, age_from, age_to)
        candidates = []
        if 'response' in search_results and search_results['response']['count'] > 0:
            users = search_results['response']['items']
            for user in users:
                # Пропускаем закрытые профили
                if user.get('is_closed', False):
                    continue
                candidates.append(user)
        return candidates

def start_search(user_id):
    if user_id not in user_search_params:
        write_msg(user_id, "Для поиска введите параметры: пол, город, возраст от, возраст до\n(например: 1, 1, 18, 30)")
        use
