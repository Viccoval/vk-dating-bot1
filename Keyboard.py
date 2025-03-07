import vk_api
import logging
from random import randrange
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

def create_keyboard(buttons=None, one_time=False):
    """ Функция создает клавиатуру."""
    keyboard = VkKeyboard(one_time=one_time)
    if not buttons:
        return keyboard.get_keyboard()
    current_line = 1
    for button in buttons:
        label = button.get('label')
        color = button.get('color', VkKeyboardColor.PRIMARY)
        line = button.get('line', current_line)  #Если не указана строка, добавляет кнопку

        if line > current_line:
            current_line = line
            keyboard.add_line()

        keyboard.add_button(label, color=color)

    return keyboard.get_keyboard()

