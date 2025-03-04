from multiprocessing.process import current_process

import requests
import configparser
import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType

from DB_love import session, User, Candidate, Favorite, Blacklist, Viewed, Photo, UserPhotoLike
from VK import vk_session, write_msg, listen_for_messages

# ------------------ Конфигурация и авторизация ------------------
config = configparser.ConfigParser()
config.read('Settings.ini')
vk_token = config['Tokens']['vk_token_gr']
vk_token_id = config['Tokens']['vk_token_id']

bot_vk_id = int(config["User_id"]["id"])

vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()
longpoll = VkLongPoll(session)

# ------------------ Глобальные переменные ------------------
user_states = {}            # Состояние пользователя
user_search_params = {}     # Параметры поиска

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
        except Exception:
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
    vk_candidate_id = candidate_data["id"]
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

# ------------------ Формирование меню ------------------
def send_main_menu(user_id):
    message = ("Главное меню:\n"
               "1. Найти кандидатов\n"
               "2. Мои избранные\n"
               "3. Мой черный список\n"
               "4. Настройки\n"
               "5. Помощь")
    write_msg(user_id, message)
    user_states[user_id] = "main_menu"

def help_menu(user_id):
    message = ("Помощь:\n"
               "Чтобы начать поиск, выберите 'Найти кандидатов'.\n"
               "В разделе 'Мои избранные' можно просматривать и удалять избранных кандидатов.\n"
               "В 'Моем черном списке' можно просматривать и удалять кандидатов, которых ты не хочешь видеть.\n"
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

# Здесь можно использовать API VK для поиска кандидатов. Можно сказать как первый код, чутка потправил и проапгрейдил.
#03.03 уже сильно проагрейдил.

class Vk_get_id:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {'access_token': access_token, 'v': version}

    def search_by_user(self, sex, city, age_from, age_to):
        url = f'{self.base_address}users.search'
        params = {
            'sex': sex,  # 1 - женщины, 2 - мужчины, 0 - по умолчанию
            'city': city,
            'age_from': age_from,
            'age_to': age_to,
            'count': 100,
            'sort': 1
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()

    def get_photo(self,user_id):
        url = f'{self.base_address}photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'count': 3
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json()

class Work_with_user(Vk_get_id):
    def __init__(self, access_token, version='5.199'):
        super().__init__(access_token, version)

    def get_users_photo(self, sex, city, age_from, age_to):
        search_results = self.search_by_user(sex, city, age_from, age_to)
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
        user_states[user_id] = "awaiting_search_params"
    else:
        write_msg(user_id, "Начинаем поиск кандидатов...")
        user_states[user_id] = {"state": "searching", "current_candidate": None}
        search_candidate(user_id)

def search_candidate(user_id):
    params = user_search_params.get(user_id)
    if not params:
        write_msg(user_id, "Ошибка: параметры поиска не заданы.")
        send_main_menu(user_id)
        return
    work = Work_with_user(vk_token_id)
    candidates = work.get_users_photo(params['sex'], params['city'], params['age_from'], params['age_to'])
    if not candidates:
        write_msg(user_id, "Кандидаты по заданным параметрам не найдены.")
        send_main_menu(user_id)
        return
# Берем первого кандидата из списка (реально стоит сохранять позицию, чтобы переходить к следующему)
    candidate = candidates[0]
    candidate_id = candidate['id']
    name = candidate.get('first_name', '')
    last_name = candidate.get('last_name', '')
    profile_url = f'https://vk.com/id{candidate_id}'
    message = (f"Кандидат найден:\n"
               f"Имя: {name} {last_name}\n"
               f"Профиль: {profile_url}\n\n"
               "Доступные команды:\n"
               "Лайк, Избранное, Следующий, Черный список")
    write_msg(user_id, message)
    user_states[user_id] = {"state": "searching", "current_candidate": candidate}

def process_search_action(user_id, text):
    state_info = user_states.get(user_id)
    if not isinstance(state_info, dict) or "current_candidate" not in state_info:
        write_msg(user_id, "Ошибка состояния поиска. Возвращаемся в главное меню.")
        send_main_menu(user_id)
        return
    candidate = state_info["current_candidate"]
    candidate_obj = get_or_create_candidate(candidate)
    user_obj = get_or_create_user(user_id)
    if text.lower() ==  "лайк":
        write_msg(user_id, f"Вы поставили лайк кандидату {candidate.get('first_name', '')} {candidate.get('last_name', '')}.")
        # В лучшем варианте тут тыкнуть логику авто отправке лайка
    elif text.lower() == "избранное":
        existing_fav = session.query(Favorite).filter_by(user_id=user_obj.user_id, candidate_id=candidate_obj.candidate_id).first()
        if not existing_fav:
            fav = Favorite(user_id=user_obj.user_id, candidate_id=candidate_obj.candidate_id)
            session.add(fav)
            session.commit()
            write_msg(user_id, f"Кандидат {candidate_obj.first_name} {candidate_obj.last_name} добавлен в избранное.")
        else:
            write_msg(user_id, "Кандидат уже в избранных.")
    elif text.lower() in ["черный список", "в черный список"]:
        existing_bl = session.query(Blacklist).filter_by(user_id=user_obj.user_id, candidate_id=candidate_obj.candidate_id).first()
        if not existing_bl:
            bl = Blacklist(user_id=user_obj.user_id, candidate_id=candidate_obj.candidate_id)
            session.add(bl)
            session.commit()
            write_msg(user_id,
                      f"Кандидат {candidate_obj.first_name} {candidate_obj.last_name} добавлен в черный список.")
        else:
            write_msg(user_id, "Кандидат уже в черном списке.")
    elif text.lower() == "следующий":
        write_msg(user_id, "Переходим к следующему кандидату.")
        viewed = Viewed(user_id=user_obj.user_id, candidate_id=candidate_obj.candidate_id)
        session.add(viewed)
        session.commit()
    else:
        write_msg(user_id, "Неизвестная команда в режиме поиска.")
    search_candidate(user_id) # это поиск следующего!!!!!!!!!!!

def process_favorites(user_id, text):
    user_obj = get_or_create_user(user_id)
    if text.lower() == "просмотр":
        favs = session.query(Favorite).filter_by(user_id=user_obj.user_id).all()
        if not favs:
            write_msg(user_id, "Список избранных пуст.")
        else:
            message = "Ваши избранные кандидаты:\n"
            for idx, fav in enumerate(favs, start=1):
                candidate = fav.candidate
                message += f"{idx}. {candidate.first_name} {candidate.last_name} - {candidate.profile_link}\n"
            write_msg(user_id, message)
    elif text.lower().startswith("удалить"):
        try:
            parts = text.split()
            index = int(parts[-1]) - 1
            favs = session.query(Favorite).filter_by(user_id=user_obj.user_id).all()
            if 0 <= index < len(favs):
                session.delete(favs[index])
                session.commit()
                write_msg(user_id, "Кандидат удалён из избранных.")
            else:
                write_msg(user_id, "Неверный номер кандидата.")

        except Exception as e:
            write_msg(user_id, f"Ошибка при удалении: {str(e)}")

    else:
        write_msg(user_id, "Неизвестная команда для работы с избранными.")
    send_main_menu(user_id)
def process_blacklist(user_id, text):
    user_obj = get_or_create_user(user_id)
    if text.lower() == "просмотр":
        bls = session.query(Blacklist).filter_by(user_id=user_obj.user_id).all()
        if not bls:
            write_msg(user_id, "Черный список пуст.")
        else:
            message = "Ваш черный список:\n"
            for idx, bl in enumerate(bls, start=1):
                candidate = bl.candidate
                message += f"{idx}. {candidate.first_name} {candidate.last_name} - {candidate.profile_link}\n"
            write_msg(user_id, message)
    elif text.lower().startswith("удалить"):
        try:
            parts = text.split()
            index = int(parts[1]) - 1
            bls = session.query(Blacklist).filter_by(user_id=user_obj.user_id).all()
            if 0 <= index < len(bls):
                session.delete(bls[index])
                session.commit()
                write_msg(user_id, "Кандидат удалён из черного списка.")
            else:
                write_msg(user_id, "Неверный номер кандидата.")
        except Exception as e:
            write_msg(user_id, f"Ошибка при удалении: {str(e)}")
    else:
        write_msg(user_id, "Неизвестная команда для работы с черным списком.")
    send_main_menu(user_id)

def listen_for_message():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id_event = event.user_id
            request = event.text.strip()
            user_obj = get_or_create_user(user_id_event)
            if not user_obj.first_name:
                if user_states.get(user_id_event) != "awaiting_registration":
                    write_msg(user_id_event,
                              "Добро пожаловать! Введите, пожалуйста, данные регистрации в формате:\nИмя, Фамилия, возраст, пол, город")
                    user_states[user_id_event] = "awaiting_registration"
                else:
                    process_registration(user_id_event, request)
                continue

            # new чеак
            if user_id_event not in user_states or user_states[user_id_event] == "main_menu":
                if request.lower() in ["найти кандидатов", "1"]:
                    start_search(user_id_event)
                elif request.lower() in ["мои избранные", "2"]:
                    write_msg(user_id_event,
                              "Введите 'просмотр' для просмотра избранных или 'удалить [номер]' для удаления.")
                    user_states[user_id_event] = "favorites"
                elif request.lower() in ["мой черный список", "3"]:
                    write_msg(user_id_event,
                              "Введите 'просмотр' для просмотра черного списка или 'удалить [номер]' для удаления.")
                    user_states[user_id_event] = "blacklist"
                elif request.lower() in ["настройки", "4"]:
                    settings_menu(user_id_event)
                elif request.lower() in ["помощь", "5"]:
                    help_menu(user_id_event)
                else:
                    send_main_menu(user_id_event)
            else:
                current_state = user_states[user_id_event]
                if isinstance(current_state, dict) and current_state.get('state') == "searching":
                    process_search_action(user_id_event, request)
                elif current_state == "awaiting_search_params":
                    process_settings(user_id_event, request)
                elif current_state == "settings":
                    process_settings(user_id_event, request)
                elif current_state == "favorites":
                    process_favorites(user_id_event, request)
                elif current_state == "blacklist":
                    process_blacklist(user_id_event, request)
                elif current_state == "awaiting_registration":
                    process_registration(user_id_event, request)
                else:
                    send_main_menu(user_id_event)

if __name__ == "__main__":
    send_main_menu(bot_vk_id)
    listen_for_message()














