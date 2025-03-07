from Logic_bot import *
from vk_api.longpoll import VkLongPoll, VkEventType
import logging

def listen_for_message():
    """Функция для прослушивания сообщения от пользователя"""
    logging.info("Сессия API VK успешно началась.")
    logging.info("Бот слушает пользователя.")

    for event in longpoll.listen():

        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id_event = event.user_id
            request = event.text.strip()
            user_obj = get_or_create_user(user_id_event)
            logging.info(f"Получено сообщение от {user_id_event}: {request}")

            if not user_obj.first_name:
                handle_new_user(user_id_event, request)
            else:
                handle_existing_user(user_id_event, request)


def handle_new_user(user_id_event, request):
    """Обрабатывает новых пользователей, которые ещё не зарегистрированы"""
    if user_states.get(user_id_event) != "awaiting_registration":

        user_name = Work_with_user(vk_token_id).get_name_user(user_id=user_id_event)
        if user_name:
            write_msg(user_id_event,
                f"Добро пожаловать, {user_name}! Введите, пожалуйста,"
                  " данные регистрации в формате:\nИмя, Фамилия, возраст, пол, город")
        else:
            write_msg(user_id_event,
                f"Добро пожаловать! Введите, пожалуйста,"
                      " данные регистрации в формате:\nИмя, Фамилия, возраст, пол, город")
        user_states[user_id_event] = "awaiting_registration"
    else:
        process_registration(user_id_event, request)
    handle_existing_user(user_id_event, request)


def handle_existing_user(user_id_event, request):
    """Обрабатывает сообщения от уже зарегистрированных пользователей"""
    if user_id_event not in user_states or user_states[user_id_event] == "main_menu":
        handle_main_menu_selection(user_id_event, request)
    else:
        process_user_state(user_id_event, request)


def handle_main_menu_selection(user_id_event, request):
    """Обрабатывает выбор пользователя из главного меню"""
    logging.info(f"Обрабатываем запрос: {request} от пользователя: {user_id_event}")
    vk_get = Vk_get_id(user_id_event)
    if request.lower() in ["найти кандидатов", "1"]:
        if user_id_event not in user_search_params:
            logging.info(f"Параметры поиска не найдены для"
                         f" пользователя {user_id_event}, работает start_search.")
            start_search(user_id_event)
        else:
            logging.info(f"Параметры поиска уже есть для пользователя"
                         f" {user_id_event}, теперь работа за search_candidate.")
            search_candidate(user_id_event)

    elif request.lower() in ["мои избранные", "2"]:
        handle_favorites(user_id_event)
    elif request.lower() in ["мой черный список", "3"]:
        handle_blacklist(user_id_event)
    elif request.lower() in ["настройки", "4"]:
        settings_menu(user_id_event)
    elif request.lower() in ["помощь", "5"]:
        help_menu(user_id_event)
    else:
        send_main_menu(user_id_event)


def handle_favorites(user_id_event):
    """Обрабатывает действия, связанные с избранными"""
    buttons = [
        {"label": "Просмотр", "color": VkKeyboardColor.SECONDARY},
        {"label": "Удалить", "color": VkKeyboardColor.SECONDARY},
    ]
    keyboard = create_keyboard(buttons=buttons)
    write_msg(user_id_event,
              "Введите 'просмотр' для просмотра избранных или 'удалить [номер]'"
              " для удаления.", keyboard=keyboard)
    user_states[user_id_event] = "favorites"


def handle_blacklist(user_id_event):
    """Обрабатывает действия, связанные с черным списком"""
    buttons = [
        {"label": "Просмотр", "color": VkKeyboardColor.SECONDARY},
        {"label": "Удалить", "color": VkKeyboardColor.SECONDARY},
    ]
    keyboard = create_keyboard(buttons=buttons)
    write_msg(user_id_event,
              "Введите 'просмотр' для просмотра черного списка или 'удалить [номер]'"
              " для удаления.", keyboard=keyboard)
    user_states[user_id_event] = "blacklist"


def process_user_state(user_id_event, request):
    """Обрабатывает действия в зависимости от текущего состояния пользователя"""
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


# def listen_for_message():
#     """Функция для прослушивания сообщения от пользователя"""
#     logging.info("Сессия API VK успешно началась.")
#     logging.info("Бот слушает пользователя.")
#     for event in longpoll.listen():
#         if event.type == VkEventType.MESSAGE_NEW and event.to_me:
#             user_id_event = event.user_id
#             request = event.text.strip()
#
#             user_obj = get_or_create_user(user_id_event)
#             logging.info(f"Получено сообщение от {user_id_event}: {request}")
#             if not user_obj.first_name:
#                 if user_states.get(user_id_event) != "awaiting_registration":
#                     write_msg(user_id_event,
#                               f"Добро пожаловать,! Введите, пожалуйста,"
#                               " данные регистрации в формате:\nИмя, Фамилия, возраст, пол, город")
#                     user_states[user_id_event] = "awaiting_registration"
#                 else:
#                     process_registration(user_id_event, request)
#                 continue
#
#             # new чеак
#             if user_id_event not in user_states or user_states[user_id_event] == "main_menu":
#                 if request.lower() in ["найти кандидатов", "1"]:
#                     start_search(user_id_event)
#                 elif request.lower() in ["мои избранные", "2"]:
#                     buttons = [
#                         {"label": "Просмотр", "color": VkKeyboardColor.SECONDARY},
#                         {"label": "Удалить", "color": VkKeyboardColor.SECONDARY},
#                     ]
#                     keyboard = create_keyboard(buttons=buttons)
#                     write_msg(user_id_event,
#                               "Введите 'просмотр' для просмотра избранных или 'удалить [номер]'"
#                               " для удаления.", keyboard=keyboard)
#                     user_states[user_id_event] = "favorites"
#                 elif request.lower() in ["мой черный список", "3"]:
#                     buttons = [
#                         {"label": "Просмотр", "color": VkKeyboardColor.SECONDARY},
#                         {"label": "Удалить", "color": VkKeyboardColor.SECONDARY},
#                     ]
#                     keyboard = create_keyboard(buttons=buttons)
#                     write_msg(user_id_event,
#                               "Введите 'просмотр' для просмотра черного"
#                               " списка или 'удалить [номер]' для удаления.", keyboard=keyboard)
#                     user_states[user_id_event] = "blacklist"
#                 elif request.lower() in ["настройки", "4"]:
#                     settings_menu(user_id_event)
#                     if request.lower() in ["назад"]:
#                         send_main_menu(user_id_event)
#                 elif request.lower() in ["помощь", "5"]:
#                     help_menu(user_id_event)
#                     if request.lower() in ["назад"]:
#                         send_main_menu(user_id_event)
#                 else:
#                     send_main_menu(user_id_event)
#             else:
#                 current_state = user_states[user_id_event]
#                 if isinstance(current_state, dict) and current_state.get('state') == "searching":
#                     process_search_action(user_id_event, request)
#                 elif current_state == "awaiting_search_params":
#                     process_settings(user_id_event, request)
#                 elif current_state == "settings":
#                     process_settings(user_id_event, request)
#                 elif current_state == "favorites":
#                     process_favorites(user_id_event, request)
#                 elif current_state == "blacklist":
#                     process_blacklist(user_id_event, request)
#                 elif current_state == "awaiting_registration":
#                     process_registration(user_id_event, request)
#                 else:
#                     send_main_menu(user_id_event)


if __name__ == "__main__":
    send_main_menu(bot_vk_id)
    listen_for_message()
