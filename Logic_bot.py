from multiprocessing.process import current_process

import requests
import configparser
import logging
import vk_api
from random import randrange
from Keyboard import *
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
longpoll = VkLongPoll(vk_session)

# ------------------ Глобальные переменные ------------------
user_states = {}            # Состояние пользователя
user_search_params = {}     # Параметры поиска

#-----------------------Настройка логирования--------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ------------------ Работа с БД ------------------
def get_or_create_user(vk_id):
    """Функция ищет пользователя по vk_id в БД, или создает нового; возвращает пользователя"""
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
    """Функция обрабатывает новые значение, введенные пользователем, в
        Формате: Имя, Фамилия, возраст, пол, город, обновляет их и добавляет в БД"""
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
        write_msg(user_vk_id, f"Ошибочная попытка в: {str(e)}. Попробуй еще раз,"
                              f" только попробуй думать и напиши в формате: Имя, Фамилия, возраст, пол, город")

def get_or_create_candidate(candidate_data):
    """Функция получает [id] пользователя, ищет в БД, добавляет нового, если не найден"""
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

def write_msg(user_id, message, keyboard=None):
    """Функция отправляет сообщение пользователю"""
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=randrange(10 ** 7),
            keyboard=keyboard
        )
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка API при отправке сообщения: {e}")

# ------------------ Формирование меню ------------------
def send_main_menu(user_id):
    """Функция отправляет главное меню пользователю"""
    buttons = [
        {"label": "Найти кандидатов", "color": VkKeyboardColor.SECONDARY, "line": 1},
        {"label": "Мои избранные", "color": VkKeyboardColor.PRIMARY, "line": 1},
        {"label": "Мой черный список", "color": VkKeyboardColor.NEGATIVE, "line": 2},
        {"label": "Настройки", "color": VkKeyboardColor.POSITIVE, "line": 2},
        {"label": "Помощь", "color": VkKeyboardColor.SECONDARY, "line": 2}
    ]
    keyboard = create_keyboard(buttons=buttons)
    message = ("Главное меню:\n"
               "1. Найти кандидатов\n"
               "2. Мои избранные\n"
               "3. Мой черный список\n"
               "4. Настройки\n"
               "5. Помощь")
    write_msg(user_id, message, keyboard=keyboard)
    user_states[user_id] = "main_menu"

def help_menu(user_id):
    """Функция отправляет раздел "помощь" пользователю"""
    buttons = [
        {"label": "Найти кандидатов", "color": VkKeyboardColor.SECONDARY, "line": 1},
        {"label": "Мои избранные", "color": VkKeyboardColor.PRIMARY, "line": 1},
        {"label": "Мой черный список", "color": VkKeyboardColor.NEGATIVE, "line": 2},
        {"label": "Настройки", "color": VkKeyboardColor.SECONDARY, "line": 2},
        {"label": "Помощь", "color": VkKeyboardColor.POSITIVE, "line": 2}
    ]
    keyboard = create_keyboard(buttons=buttons)
    message = ("Помощь:\n"
               "Чтобы начать поиск, выберите 'Найти кандидатов'.\n"
               "В разделе 'Мои избранные' можно просматривать и удалять избранных кандидатов.\n"
               "В 'Моем черном списке' можно просматривать и удалять кандидатов, которых ты не хочешь видеть.\n"
               "В 'Настройках' можно изменить параметры поиска.\n"
               "При поиске доступны команды:\n"
               "Лайк, Избранное, Следующий, Черный список")
    write_msg(user_id, message, keyboard=keyboard)
    send_main_menu(user_id)

def settings_menu(user_id):
    """Функция отправляет настройки поиска пользователю"""

    message = ("Настройки поиска:\n"
               "Введите новые параметры в формате:\n"
               "пол, город, возраст от, возраст до\n"
               "Например: 1, 1, 18, 30")
    write_msg(user_id, message)

def process_settings(user_id, text):
    """Функция получает параметры, введенные пользователем
    и добавляет к глобальной переменной user_search_params"""
    try:
        parts = [part.strip() for part in text.split(',')]
        if len(parts) != 4:
            raise ValueError("Снова угараешь. Необходимо ввести 4 параметра:"
                             " пол, город, возраст от, возраст до "
                             "(например: 1, 1, 18, 30)")
        try:
            sex = int(parts[0])
            city = int(parts[1])
            age_from = int(parts[2])
            age_to = int(parts[3])
        except ValueError:
            raise ValueError("Все параметры должны быть числами. Например: 1, 1, 18, 30")
        user_search_params[user_id] = {
            'sex': sex,
            'city': city,
            'age_from': age_from,
            'age_to': age_to
        }
        write_msg(user_id, "Ты на карандаше!")
    except ValueError as e:
        write_msg(user_id, f"Ошибка: {str(e)}. Плиз трайн эгейн.")
        return
    send_main_menu(user_id)


class Vk_get_id:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {'access_token': access_token, 'v': version}

    def search_by_user(self, sex, city, age_from, age_to):
        """Функция для поиска людей по параметрам"""
        url = f'{self.base_address}users.search'
        params = {
            'sex': sex,
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
        """Функция ищет три фотографии пользователя, берет их из профиля"""
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
        """Выполняет поиск пользователей, фильтруя закрытые профили"""
        search_results = self.search_by_user(sex, city, age_from, age_to)
        logging.info(f"Результаты поиска: {search_results}")
        candidates = []

        if 'response' in search_results and search_results['response']['count'] > 0:
            users = search_results['response']['items']
            for user in users:
                # Пропускаем закрытые профили
                if user.get('is_closed', False):
                    continue
                candidates.append(user)

            return candidates

    def get_name_user(self, user_id):
        """Функция получает имя пользователя"""
        url = f'{self.base_address}users.get'
        params = {
            'user_ids': user_id,
        }
        params.update(self.params)
        save = requests.get(url, params=params)
        response = save.json()
        try:
            dict_info_about_users = response['response']
            if dict_info_about_users:
                first_name = dict_info_about_users[0].get('first_name')
                return first_name
        except KeyError:
            write_msg(user_id, 'Ошибка получения данных')
            return None

def start_search(user_id):
    """ Функция начинает поиск кандитата, отправляет ему сообщение """
    logging.info(f"Запускаем поиск для пользователя {user_id}.")
    if user_id not in user_search_params:
        write_msg(user_id, "Для поиска введите параметры: пол,"
                           " город, возраст от, возраст до\n"
                           "(например: 1(где 1-женщины, 2-мужчины), 1, 18, 30)")
        user_states[user_id] = "awaiting_search_params"
    else:
        write_msg(user_id, "Начинаем поиск кандидатов...")
        user_states[user_id] = {"state": "searching", "current_candidate": None}
        search_candidate(user_id)

def search_candidate(user_id):
    """Функция ищет пользователя по параметрам из глобальной переменной,
     возвращает пользователю Имя, Профиль"""
    params = user_search_params.get(user_id)
    work = Work_with_user(vk_token_id)
    candidates = work.get_users_photo(params['sex'], params['city'], params['age_from'], params['age_to'])
    if not candidates:
        write_msg(user_id, "Кандидаты по заданным параметрам не найдены.")
        send_main_menu(user_id)
        return

    current_state = user_states.get(user_id, {})
    if not isinstance(current_state, dict):
        current_state = {}

    already_shown_candidates = current_state.get("shown_candidates", [])
    candidate = None
    for c in candidates:
        candidate_id = c.get('id')
        if candidate_id not in already_shown_candidates:
            existing_candidate = session.query(Candidate).filter_by(vk_id=candidate_id).first()
            if not existing_candidate:
                candidate = c
                break

    if not candidate:
        write_msg(user_id, "Ты просмотрел всех!")
        send_main_menu(user_id)
        return
    #В список показанных
    already_shown_candidates.append(candidate['id'])
    # Обновить состояние пользователя
    user_states[user_id] = {
        "state": "searching",
        "current_candidate": candidate,
        "shown_candidates": already_shown_candidates
    }

    candidate_id = candidate['id']
    name = candidate.get('first_name', '')
    last_name = candidate.get('last_name', '')
    profile_url = f'https://vk.com/id{candidate_id}'


    #Фото выдают ошибку!!!!!
    # photos = work.get_photo(candidate_id)
    # attachments = []
    # if photos and 'response' in photos:
    #     if isinstance(photos['response'], list):
    #         for photo in photos['response']:
    #             if isinstance(photo, dict):
    #                 photo_url = f"photo{photo['owner_id']}_{photo['id']}"
    #                 attachments.append(photo_url)
    #     else:
    #         write_msg(user_id, "Ошибка: фотографии не найдены.")
    #         send_main_menu(user_id)
    #         return
    message = (f"Кандидат найден:\n"
               f"Имя: {name} {last_name}\n"
               f"Профиль: {profile_url}\n\n"
               "Доступные команды:\n"
               "Лайк, Избранное, Следующий, Черный список")

    buttons = [
        {"label": "Лайк", "color": VkKeyboardColor.POSITIVE, "line": 1},
        {"label": "Избранное", "color": VkKeyboardColor.PRIMARY, "line": 1},
        {"label": "Следующий", "color": VkKeyboardColor.SECONDARY, "line": 2},
        {"label": "Черный список", "color": VkKeyboardColor.NEGATIVE, "line": 2}
    ]
    keyboard = create_keyboard(buttons=buttons)
    write_msg(user_id, message, keyboard=keyboard)
    user_states[user_id] = {"state": "searching", "current_candidate": candidate}

def send_like(vk_session, user_id, photo_id):
    """Функция для отправки лайка на фото"""
    vk = vk_session.get_api()
    try:
        vk.likes.add(type='photo', owner_id=user_id, item_id=photo_id)
        return True
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при отправке лайка: {e}")
        return False

def process_search_action(user_id, text):
    """Функция работает с текущим кандитатом, добавляет в разные таблицы БД, ставит лайк"""
    state_info = user_states.get(user_id)
    if not isinstance(state_info, dict) or "current_candidate" not in state_info:
        write_msg(user_id, "Ошибка состояния поиска. Возвращаемся в главное меню.")
        send_main_menu(user_id)
        return
    candidate = state_info["current_candidate"]
    candidate_obj = get_or_create_candidate(candidate)
    user_obj = get_or_create_user(user_id)
    if text.lower() ==  "лайк":
        candidate_photo_id = candidate.get('photo_id')
        candidate_id = candidate.get('id')
        if candidate_photo_id:
            success = send_like(vk_session, candidate_id, candidate_photo_id)
            if success:
                write_msg(user_id,
                          f"Вы поставили лайк на фото кандидата {candidate.get('first_name', '')} {candidate.get('last_name', '')}.")
            else:
                write_msg(user_id, "Произошла ошибка при отправке лайка.")
        else:
            write_msg(user_id, "Не удалось найти фото для лайка.")
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
    """Функция работает с избранными: просмотр, удалить"""

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
    """Функция работает с черным списком: просмотр, удалить"""
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



