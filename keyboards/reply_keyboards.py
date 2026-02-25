from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_keyboard(
        *,
        btns: list[str],
        placeholder: str = None,
        request_contact: int | list[int] = None,
        request_location: int | list[int] = None,
        sizes: tuple[int] = (2,)):

    keyboard = ReplyKeyboardBuilder()

    if isinstance(request_contact, int):
        request_contact = [request_contact]
    if isinstance(request_location, int):
        request_location = [request_location]

    for index, value in enumerate(btns):
        request_contact_flag = request_contact and index in request_contact
        request_location_flag = request_location and index in request_location

        keyboard.add(KeyboardButton(
            text=value,
            request_contact=request_contact_flag,
            request_location=request_location_flag
        ))

    return keyboard.adjust(*sizes).as_markup(resize_keyboard=True, input_field_placeholder=placeholder)
