import os
import openai
from decimal import Decimal

from aiogram import Router, F, Bot, types
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile

from database.connection import get_connection
from filters.chat_type_filter import ChatTypeFilter
from keyboards.inline_keyboards import get_callback_button
from keyboards.reply_keyboards import get_keyboard

from dotenv import load_dotenv

from services.ai_assistant import get_ai_response

from services.pump_calculator import (
    calculate_irrigation_flow,
    calculate_pump_requirement,
    convert_area_to_m2,
    normalize_number,
)

load_dotenv()

regular_users_router = Router()
regular_users_router.message.filter(ChatTypeFilter(['private']))

START_BUTTONS = get_keyboard(btns=['Індивідуальні оптові ціни',
                                   'Розрахунок системи поливу',
                                   'Зворотний зв’язок',
                                   'Моє страхування',
                                   'Про компанію',
                                   'Інтелектуальний помічник TechBaza'],
                             sizes=(2, 3, 1))


########################################################################################################################
################################################# START ################################################################
########################################################################################################################
@regular_users_router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await message.answer('Вітаємо у боті <b>TechBaza</b>!',
                         reply_markup=START_BUTTONS)
    await state.clear()


@regular_users_router.callback_query(F.data == 'main_regular_user')
async def start_after_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Вітаємо у боті <b>TechBaza</b>!',
                                  reply_markup=START_BUTTONS)
    await state.clear()


########################################################################################################################
##################################################### КАЛЬКУЛЯТОР ######################################################
########################################################################################################################
class PumpCal(StatesGroup):
    enter_area = State()
    enter_area_ones = State()

    enter_row_spacing = State()
    enter_emitter_spacing = State()
    enter_emitter_flow = State()

    enter_pipe_diameter = State()
    enter_pipe_length = State()
    enter_height_difference = State()

    final = State()

@regular_users_router.message(F.text == 'Розрахунок системи поливу')
async def pump_cal_start(message: Message, state: FSMContext):
    await message.answer(
        'Введіть площу поля:\n\n'
        'Наприклад: 5000, 50 або 1.5',
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(PumpCal.enter_area)


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_area))
async def pump_cal_area(message: Message, state: FSMContext):
    try:
        area = normalize_number(message.text)
        if area <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть площу числом. Наприклад: 5000 або 1.5'
        )
        return

    await state.update_data(area=area)

    await message.answer(
        'Оберіть одиниці площі:',
        reply_markup=get_callback_button(
            btns={
                'м²': 'm2',
                'сотки': 'hundreds',
                'га': 'ga',
            },
            sizes=(3,)
        )
    )
    await state.set_state(PumpCal.enter_area_ones)


@regular_users_router.callback_query(
    F.data.in_(['m2', 'hundreds', 'ga']),
    StateFilter(PumpCal.enter_area_ones)
)
async def pump_cal_area_ones(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    area = data['area']
    area_unit = callback.data

    area_m2 = convert_area_to_m2(area, area_unit)
    await state.update_data(area_m2=area_m2)

    await callback.message.answer(
        'Введіть відстань між рядками в метрах:\n\n'
        'Наприклад: 0.7'
    )
    await state.set_state(PumpCal.enter_row_spacing)


@regular_users_router.message(StateFilter(PumpCal.enter_area_ones))
async def pump_cal_area_ones_problem(message: Message, state: FSMContext):
    await message.answer(
        'Оберіть одиниці через кнопки:',
        reply_markup=get_callback_button(
            btns={
                'м²': 'm2',
                'сотки': 'hundreds',
                'га': 'ga',
            },
            sizes=(3,)
        )
    )


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_row_spacing))
async def pump_cal_row_spacing(message: Message, state: FSMContext):
    try:
        row_spacing = normalize_number(message.text)
        if row_spacing <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть відстань між рядками в метрах. Наприклад: 0.7'
        )
        return

    await state.update_data(row_spacing=row_spacing)

    await message.answer(
        'Введіть крок емітера в метрах:\n\n'
        'Наприклад:\n'
        '0.1 — 10 см\n'
        '0.2 — 20 см\n'
        '0.3 — 30 см'
    )
    await state.set_state(PumpCal.enter_emitter_spacing)


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_emitter_spacing))
async def pump_cal_emitter_spacing(message: Message, state: FSMContext):
    try:
        emitter_spacing = normalize_number(message.text)
        if emitter_spacing <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть крок емітера в метрах. Наприклад: 0.3'
        )
        return

    await state.update_data(emitter_spacing=emitter_spacing)

    await message.answer(
        'Введіть витрату одного емітера в л/год:\n\n'
        'Наприклад: 1.1 або 1.4'
    )
    await state.set_state(PumpCal.enter_emitter_flow)


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_emitter_flow))
async def pump_cal_emitter_flow(message: Message, state: FSMContext):
    try:
        emitter_flow = normalize_number(message.text)
        if emitter_flow <= 0:
            raise ValueError

        data = await state.get_data()

        irrigation_result = calculate_irrigation_flow(
            area_m2=data['area_m2'],
            row_spacing_m=data['row_spacing'],
            emitter_spacing_m=data['emitter_spacing'],
            emitter_flow_l_h=emitter_flow,
        )

    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть витрату одного емітера в л/год. Наприклад: 1.4'
        )
        return

    await state.update_data(
        emitter_flow=emitter_flow,
        total_tape_length_m=irrigation_result.total_tape_length_m,
        total_emitters=irrigation_result.total_emitters,
        required_flow_l_h=irrigation_result.required_flow_l_h,
        required_flow_m3_h=irrigation_result.required_flow_m3_h,
    )

    await message.answer(
        f'<b>Попередній розрахунок продуктивності</b>:\n\n'
        f'Довжина крапельної стрічки: <b>{irrigation_result.total_tape_length_m:.2f}</b> м\n'
        f'Кількість емітерів: <b>{irrigation_result.total_emitters:.0f}</b> шт.\n'
        f'Загальна витрата води: <b>{irrigation_result.required_flow_m3_h:.2f}</b> м³/год\n\n'
        f'Тепер розрахуємо орієнтовні втрати напору в магістральній трубі.\n'
        f'Оберіть діаметр труби ПНД:',
        reply_markup=get_callback_button(
            btns={
                'Ø20': 'pipe_20',
                'Ø25': 'pipe_25',
                'Ø32': 'pipe_32',
                'Ø40': 'pipe_40',
                'Ø50': 'pipe_50',
                'Ø63': 'pipe_63',
                'Ø75': 'pipe_75',
            },
            sizes=(3, 2, 2)
        )
    )

    await state.set_state(PumpCal.enter_pipe_diameter)


@regular_users_router.callback_query(
    F.data.in_(['pipe_20', 'pipe_25', 'pipe_32', 'pipe_40', 'pipe_50', 'pipe_63', 'pipe_75']),
    StateFilter(PumpCal.enter_pipe_diameter)
)
async def pump_cal_pipe_diameter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    pipe_diameter = int(callback.data.replace('pipe_', ''))
    await state.update_data(pipe_diameter=pipe_diameter)

    await callback.message.answer(
        'Введіть довжину магістральної труби від насоса до ділянки, м:\n\n'
        'Наприклад: 100 або 250'
    )
    await state.set_state(PumpCal.enter_pipe_length)


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_pipe_length))
async def pump_cal_pipe_length(message: Message, state: FSMContext):
    try:
        pipe_length = normalize_number(message.text)
        if pipe_length < 0:
            raise ValueError
    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть довжину магістралі в метрах. Наприклад: 100'
        )
        return

    await state.update_data(pipe_length=pipe_length)

    await message.answer(
        'Введіть перепад висоти в метрах:\n\n'
        '0 — якщо насос і поле приблизно на одному рівні\n'
        '5 — якщо поле вище насоса на 5 метрів\n'
        '-3 — якщо поле нижче насоса на 3 метри'
    )
    await state.set_state(PumpCal.enter_height_difference)


@regular_users_router.message(F.text, StateFilter(PumpCal.enter_height_difference))
async def pump_cal_final_result(message: Message, state: FSMContext):
    try:
        height_difference = normalize_number(message.text)
        data = await state.get_data()

        pump_requirement = calculate_pump_requirement(
            flow_m3_h=data['required_flow_m3_h'],
            pipe_diameter_mm=data['pipe_diameter'],
            pipe_length_m=data['pipe_length'],
            height_difference_m=height_difference,
        )

    except ValueError as error:
        await message.answer(
            f'{error}\n\n'
            f'Спробуйте повернутися до розрахунку та обрати більший діаметр труби.',
            reply_markup=get_callback_button(btns={'На головну': 'main_regular_user'})
        )
        await state.set_state(PumpCal.final)
        return

    except Exception:
        await message.answer(
            'Неправильний тип даних.\n'
            'Введіть перепад висоти в метрах. Наприклад: 0 або 5'
        )
        return

    await message.answer(
        f'<b>Результати розрахунку системи поливу</b>:\n\n'

        f'<b>1. Продуктивність</b>\n'
        f'Довжина крапельної стрічки: <b>{data["total_tape_length_m"]:.2f}</b> м\n'
        f'Кількість емітерів: <b>{data["total_emitters"]:.0f}</b> шт.\n'
        f'Загальна витрата води: <b>{data["required_flow_m3_h"]:.2f}</b> м³/год\n\n'

        f'<b>2. Втрати напору</b>\n'
        f'Діаметр магістралі: <b>Ø{data["pipe_diameter"]}</b>\n'
        f'Довжина магістралі: <b>{data["pipe_length"]:.0f}</b> м\n'
        f'Найближча витрата з таблиці: <b>{pump_requirement.nearest_table_flow_m3_h:.1f}</b> м³/год\n'
        f'Втрати в трубі: <b>{pump_requirement.pipe_loss_bar_per_100m:.2f}</b> бар / 100 м\n'
        f'Загальні втрати в трубі: <b>{pump_requirement.total_pipe_loss_bar:.2f}</b> бар\n'
        f'Перепад висоти: <b>{height_difference:.1f}</b> м = '
        f'<b>{pump_requirement.height_loss_bar:.2f}</b> бар\n'
        f'Орієнтовні втрати на фільтрі та фітингах: '
        f'<b>{pump_requirement.filter_and_fittings_loss_bar:.2f}</b> бар\n'
        f'Потрібний тиск на крапельній стрічці: '
        f'<b>{pump_requirement.drip_tape_pressure_bar:.2f}</b> бар\n\n'

        f'<b>3. Орієнтовна вимога до насоса</b>\n'
        f'Продуктивність: <b>{data["required_flow_m3_h"]:.2f}</b> м³/год\n'
        f'Напір із запасом: <b>{pump_requirement.required_head_m:.0f}</b> м\n'
        f'Тиск із запасом: <b>{pump_requirement.required_pressure_with_reserve_bar:.2f}</b> бар\n\n'

        f'Тобто насос потрібно підбирати так, щоб він міг дати приблизно '
        f'<b>{data["required_flow_m3_h"]:.2f} м³/год при {pump_requirement.required_head_m:.0f} м напору</b>.\n\n'

        f'Контакт менеджера: <b>{os.getenv("MANAGER_PHONE")}</b>\n'
        f'Для точного підбору потрібно ще врахувати джерело води, фільтр, кількість зон поливу '
        f'та реальну схему труб.',
        reply_markup=get_callback_button(btns={'На головну': 'main_regular_user'})
    )

    await state.set_state(PumpCal.final)


########################################################################################################################
####################################################### ФІДБЕК #########################################################
########################################################################################################################
class Feedback(StatesGroup):
    requested_phone = None
    to_whom = None

    start_feedback = State()
    feedback_enter_phone = State()
    feedback_enter_message = State()


@regular_users_router.message(F.text == 'Зворотний зв’язок')
async def feedback_start(message: Message, state: FSMContext):
    await message.answer('Оберіть людину, до якої бажаєте звернутися: ', reply_markup=types.ReplyKeyboardRemove())
    await message.answer('<b>Керівник</b> (з питань співробітництва)\n'
                         '<b>Менеджер</b> (з інших питань)\n'
                         '<b>Адміністратор бота</b> (з питань роботи бота)',
                         reply_markup=get_callback_button(
                             btns={'До керівника': 'До керівника',
                                   'До менеджера': 'До менеджера',
                                   'До адміністратора': 'До адміністратора'}, sizes=(2,)))
    await state.set_state(Feedback.start_feedback)


@regular_users_router.callback_query(F.data, StateFilter(Feedback.start_feedback))
async def feedback_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    to_whom = callback.data
    await state.update_data(to_whom=to_whom)

    await callback.message.answer('Тепер надішліть свій номер телефону: ',
                                  reply_markup=get_keyboard(
                                      btns=['Надіслати номер телефону'],
                                      request_contact=[0]
                                  ))
    await state.set_state(Feedback.feedback_enter_phone)


@regular_users_router.message(StateFilter(Feedback.feedback_enter_phone))
async def feedback_enter_phone(message: Message, state: FSMContext):
    try:
        phone_number = f'+{message.contact.phone_number.lstrip("+")}'
    except Exception as e:
        await message.answer('Відправте номер телефона: ', reply_markup=get_keyboard(
            btns=['Надіслати номер телефону'],
            request_contact=[0]
        ))
        return

    await state.update_data(requested_phone=phone_number)
    await message.answer('Тепер надішліть своє звернення: ', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Feedback.feedback_enter_message)


@regular_users_router.message(StateFilter(Feedback.feedback_enter_message))
async def feedback_final(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    requested_phone = data['requested_phone']
    to_whom = data['to_whom']

    requested_message = message.text if message.text else message.caption if message.caption else "Без тексту"

    media = None
    media_type = None

    if message.photo:
        media = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media = message.video.file_id
        media_type = "video"
    elif message.animation:
        media = message.animation.file_id
        media_type = "animation"
    elif message.document:
        media = message.document.file_id
        media_type = "document"
    elif message.voice:
        media = message.voice.file_id
        media_type = "voice"
    elif message.audio:
        media = message.audio.file_id
        media_type = "audio"

    await message.answer("Ваше звернення надіслано!",
                         reply_markup=get_callback_button(btns={'На головну': 'main_regular_user'}))

    text_message = (f'📩 <b>Повідомлення від:</b> {requested_phone}\n'
                    f'👤 <b>До кого:</b> {to_whom}\n\n'
                    f'💬 <b>Питання:</b> {requested_message}')

    if media:
        if media_type == "photo":
            await bot.send_photo(chat_id=-1002427051397, photo=media, caption=text_message)
        elif media_type == "video":
            await bot.send_video(chat_id=-1002427051397, video=media, caption=text_message)
        elif media_type == "animation":
            await bot.send_animation(chat_id=-1002427051397, animation=media, caption=text_message)
        elif media_type == "document":
            await bot.send_document(chat_id=-1002427051397, document=media, caption=text_message)
        elif media_type == "voice":
            await bot.send_voice(chat_id=-1002427051397, voice=media)
        elif media_type == "audio":
            await bot.send_audio(chat_id=-1002427051397, audio=media)
    else:
        await bot.send_message(chat_id=-1002427051397, text=text_message)


########################################################################################################################
###################################################### ПРО КОМПАНІЮ ####################################################
########################################################################################################################
class Info(StatesGroup):
    main_process = State()

    company_info = State()
    bot_info = State()


@regular_users_router.message(F.text == 'Про компанію')
async def about_us(message: Message, state: FSMContext):
    photo = FSInputFile("photo_2025-02-04_20-04-11.jpg")
    await message.answer_photo(photo=photo,
                               caption='Компанія «ТехБаза» – ваш незамінний партнер у виборі насосного обладнання, '
                                       'генераторів, сантехніки, автотоварів та ручного інструменту. '
                                       'Понад 10 років ми підтримуємо клієнтів з усієї України, '
                                       'допомагаючи їм знаходити ідеальні рішення для дому, саду й автомобіля. '
                                       'У нашій команді працюють не просто продавці, а досвідчені консультанти, '
                                       'які дбають про ваш комфорт та довгострокову експлуатацію обраного '
                                       'обладнання.\n\n'
                                       'Цей бот створений, аби зробити пошук потрібних товарів та отримання корисної '
                                       'інформації ще простішим'
                                       'і зручнішим. Ми маємо як фізичний магазин, де ви можете особисто ознайомитися '
                                       'з асортиментом,'
                                       'так і зручний сайт www.techbaza.ua, де легко оформити '
                                       'онлайн-замовлення.', reply_markup=types.ReplyKeyboardRemove())
    await message.answer('Якщо бажаєте дізнатися більше про «ТехБаза» або зрозуміти функціонал усіх кнопок цього бота, '
                         'натисніть «Інфо Компанії» чи «Кнопки Бота»! Ми завжди раді вам допомогти.',
                         reply_markup=get_callback_button(
                             btns={'Інфо компанії': 'company_info', 'Кнопки бота': 'bot_buttons'}))
    await state.set_state(Info.main_process)


@regular_users_router.callback_query(F.data.in_(['company_info', 'back_company', 'bot_buttons', 'back_bot']), StateFilter(Info.main_process))
async def main_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == 'company_info' or callback.data == 'back_company':
        company_btns = {'Доставка': 'shipping',
                        'Оплата': 'payment',
                        'Графік роботи': 'timetable',
                        'Повернення та обмін': 'returning',
                        'Гарантія': 'garanty',
                        'Сертифікати': 'certificates',
                        'Умови співпраці': 'cooperation',
                        '🏠 В меню': 'main_regular_user'}
        await callback.message.answer('👇 Оберіть, що вас цікавить: ', reply_markup=get_callback_button(
            btns=company_btns, sizes=(1,)
        ))
        await state.set_state(Info.company_info)
    if callback.data == 'bot_buttons' or callback.data == 'back_bot':
        bot_buttons = {'Індивідуальні оптові ціни': 'button_optprice',
                       'Розрахунок системи поливу': 'button_pumpcal',
                       'Зворотний звязок': 'button_feedback',
                       'Моє страхування': 'button_insurance',
                       'Інтелектуальний помічник': 'button_ai',
                       '🏠 В меню': 'main_regular_user'}
        await callback.message.answer('👇 Оберіть, що вас цікавить: ', reply_markup=get_callback_button(
            btns=bot_buttons, sizes=(1, )
        ))
        await state.set_state(Info.bot_info)


@regular_users_router.callback_query(F.data.in_(['shipping', 'payment', 'timetable', 'returning', 'garanty', 'certificates', 'cooperation']))
async def company_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == 'shipping':
        await callback.message.answer('''Наш інтернет магазин Техбаза надає зручні і найпопулярніші в Україні способи оплати та доставки товарів.
Бажаєте придбати зі знижкою - питайте наявність знижки у менеджера.
ЗНИЖКА НЕ ПОШИРЮЄТЬСЯ НА ОПЛАТУ ТОВАРУ З ПДВ ТА НЕ СУМУЄТЬСЯ.\n
Способи доставки
Відправка замовлень відбувається в робочі часи з понеділка по п’ятницю. Якщо замовлення оформлене після 16:00 – надсилання відбудеться наступного дня.\n
*Товари, які відсутні на момент оформлення замовлення, можуть бути відправлені протягом робочого тижня ( Вт, Пт), після поновлення залишків на склад!\n
Прийом замовлень на сайті відбувається цілодобово, і у випадку оформлення замовлення в неробочі години – буде оброблено вранці наступного дня\n
• Адресна доставка кур'єром Нової Пошти та Укрпошти по всій Україні. Вартість і умови доставки згідно тарифів Нової пошти і Укрпошти.\n
• Доставка "Укрпошта" .Вартість доставки Укрпошта згідно тарифів перевізника. Доставка по Україні від 3 до 7 днів, можливі довші терміни в залежності від локації відділення отримувача.\n
• Доставка "Самовивіз". Самовивіз здійснюється кожен день з 09.00 до 17.00 (крім суботи та неділі) 
Як оформити замовлення: Оформити замовлення на самовивіз ви можете на сайті або за телефоном: +380000000000.  
Про готовність вашого замовлення ви будете проінформовані по Viber чи SMS. 
Як отримати замовлення: Ви приїжджаєте в наш фірмовий магазин за адресою: с.Лобойківка, вул.Центральна, 125. 
Повідомляєте номер замовлення,оплачуєте та забираєте своє замовлення. Перед тим як їхати в точку самовивозу,переконайтеся, що у Вас є номер замовлення.
Ви зможете дізнатися його з листа замовлення або SmS-повідомлення.\n
• Доставка "Нова Пошта". Вартість доставки Нова Пошта становить від 70 грн залежно від ваги і габаритів вантажу. 
При виборі післяплати Ви доплачуєте 20грн+2% від вартості замовлення за повернення грошових коштів нам. 
Термін доставки від 1 до 3 робочих днів. Посилки Нова Пошта відправляються кожен день. Номери декларацій надсилаються у VIBER чи смс-повідомленням.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'payment':
        await callback.message.answer('''Способи оплати\n
• Пром-оплата. Безпечна оплата карткою. Гроші зараховуються на рахунок продавця тільки після отримання покупцем посилки, при відмові від замовлення на відділенні гроші повертаються покупцеві на картку.\n
• Післяплата "Нова Пошта". Накладений платіж здійснюється при замовленні від 300 грн. Можете заощадити цю суму, провівши повну оплату вартості товару на картку.\n
• Картка Райффайзен Банк: 4239220040100942 Геймур О.І.\n
• Готівкою. Оплата готівкою можлива на Укрпошті та при самовивезенні.\n
• Оплата за реквізитами. Формуємо рахунок на оплату для юридичних осіб і ФОП''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'timetable':
        await callback.message.answer('''Графік роботи інтернет-магазину Техбаза www.techbaza.ua\n
• Понеділок: 08:00 – 19:00\n
• Вівторок: 08:00 – 19:00\n
• Середа: 08:00 – 19:00\n
• Четвер: 08:00 – 19:00\n
• П'ятниця: 08:00 – 19:00\n
• Субота: 10:00 - 16:00\n
• Неділя: 10:00 - 16:00''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'returning':
        await callback.message.answer('''Компанія здійснює повернення і обмін товарів належної якості згідно Закону "Про захист прав споживачів».\n
Строки повернення і обміну\n
Повернення та обмін товарів можливий протягом 14 днів після отримання товару покупцем.\n
Зворотня доставка товарів здійснюється за домовленістю.\n
Умови повернення для товарів належної якості\n
Відповідно до статті 9 Закону України «Про захист прав споживачів» існує дві причини через які покупець може повернути або обміняти куплений ним товар:\n
1.  Якщо товар не відповідає якості про яку заявляв виробник;\n
2.  Якщо товар повністю відповідає всім вимогам, але з якоїсь причини не влаштовує покупця.\n
Споживач має право обміняти непродовольчий товар належної якості на аналогічний у продавця, у якого він був придбаний, якщо товар не задовольнив його за формою, габаритами, фасоном, кольором, розміром або якщо з інших причин не може бути ним використаний за призначенням. Споживач має право на обмін товару належної якості протягом 14 днів, не враховуючи день покупки.\n
Обміну товару належної якості здійснюється якщо:\n
- він не використовувався;\n
- збережено його товарний вигляд, споживчі властивості;\n
- збережені пломби, ярлики;\n
- є розрахунковий документ, виданий споживачеві разом з проданим товаром.\n
У разі, якщо товар був доставлений кур’єрською службою Нової Пошти, то його слід перевірити в присутності працівника служби при отриманні товару.\n
Умови обміну/повернення товару неналежної якості\n
Згідно статті 8 Закону України «Про захист прав споживачів» у разі виявлення протягом встановленого гарантійного строку недоліків споживач, в порядку та в строки, встановлені законодавством, має право вимагати:\n
- пропорційного зменшення ціни;\n
- безоплатного усунення недоліків товару;\n
- відшкодування витрат на усунення недоліків товару.\n
Вимоги споживача, передбачені цією статтею, не підлягають втіленню, якщо продавець, виробник (підприємство, що задовольняє вимоги споживача, встановлені частиною першою цієї статті) доведуть, що недоліки товару виникли внаслідок порушення споживачем правил користування товаром або його зберігання. Споживач має право брати участь у перевірці якості товару особисто або через свого представника.\n
Обмін та повернення товарів здійснюється поштовою компанією "Нова пошта"  Укрпошта, або за адресою: вул..Центральна, 125, с.Лобойківка, р-н.Петриківський\n\n
Для вирішення питань обміну та повернення товарів - зателефонуйте нашому менеджеру за номером +380000000000\n
Повернення коштів здійснюється зручним для клієнта способом протягом 3-х робочих днів після отримання та перевірки продавцем товару.\n
Відповідно закону "Про захист прав споживачів», компанія може відмовити споживачеві в обміні та поверненні товарів належної якості, якщо вони відносяться до категорій, зазначених у чинному Переліку непродовольчих товарів належної якості, що не підлягають поверненню та обміну.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'garanty':
        await callback.message.answer('''Наша компанія Техбаза є офіційним представником ряду провідних компаній виробників насосів і насосного обладнання на ринку України.\n
Офіційний сервіс здійснює ряд ремонтних і гарантійних ремонтів насосного обладнання (в тому числі свердловинних насосів) таких брендів: «Aquatica», «LEO», «Dongyin», «Wetron».\n
Компанії, які є виробниками надають гарантію в середньому від 12 до 24 місяців в залежності від типу обладнання. В кожному товарі, представленому на нашому сайті зазначений період гарантії.\n
Як скористатися послугами сервісного центру інтернет магазину Techbaza.ua:\n
Перше, що Вам необхідно зробити – це зателефонувати нашим фахівцям і пояснити проблему, з якою Ви зіткнулися і що саме не працює в обладнанні. Після цього фахівці підкажуть яку інформацію про продукцію Вам необхідно вказати: модель, серійний номер, дату покупки, Ваші ПІБ адреса і телефон. Після цього Ви зможете оформити заявку і відправити товар в сервісний центр, де в максимально короткий період буде проведена вся необхідна робота.\n
Послуги нашого центру охоплюють всю Україну і тому ми приймаємо насоси та обладнання для ремонту зі всієї території країни за допомогою послуг перевізника "Нова Пошта".\n
Купуючи обладнання у нас Ви можете бути впевнені в якості товару і в разі необхідності можете скористатися гарантійним обслуговуванням.\n
Ми цінуємо нашу репутацію і клієнтів, які придбали у нас продукцію – тому Ви можете звернутися до нас в робочі години: з 08:00 до 17:00 у будні дні за номерами телефонів: +380000000000, +380000000000.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'certificates':
        await callback.message.answer('''Для сучасних споживачів, як оптових, так і роздрібних, сертифікація є невід'ємною частиною будь-якого продукту або послуги. З точки зору продажів одна з основних задач виробника і / або постачальника - переконати потенційного покупця в тому, що заявлені властивості товару повністю збігаються з фактичними. Це єдиний спосіб, яким компанія може в повній мірі скористатися, щоб домогтися конкурентної переваги своєї пропозиції і комерційного успіху. У цьому сенсі сертифікація є важливим інструментом для створення правильного іміджу товарів / послуг і збільшення попиту в майбутньому. Саме тому на кожен з представлених товарів в інтернет магазині www.techbaza.ua є вся необхідна документація. У тому числі і сертифікати УкрСЕПРО, що показує якість і легальність імпортованої продукції, яка представлена на сайті.\n\n
Всі товари мають необхідні документи і сертифікати, які свідчать про їх високу якість і надійність. А так як наша компанія techbaza.ua є зареєстрованою торговою маркою і офіційним представником в Україні заводів виробників - Ви можете бути впевнені в сервісі і гарантійному обслуговуванні після покупки.\n\n
Сертифікати на товари в інтернет магазині www.techbaza.ua\n\n
Компанії «LEO», «Aquatica», «Dongyin», «Sigma», «TAU», «Wetron», і «Katran» є професійними компаніями виробниками насосів води, сантехніки та генераторів, які представлені в категоріях нашого інтернет магазину. Саме продукція цих компаній має хороші характеристики, доступні ціни та використовується в багатьох країнах світу. Сертифікати на товари цих виробників представлені на нашому сайті, а також можна отримати за першим запитом покупця до кожної окремо взятої продукції. Для цього Ви можете зв'язатися з нашими консультантами за телефонами, які є на сайті і Вам буде надана вся необхідна документація та інформація по вибраному Вами товару.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'cooperation':
        await callback.message.answer('''Techbaza.ua - це добре оснащений оптовий продавець гідравлічного обладнання. Ми працюємо в галузі двадцять років, і за цей час накопичили необхідний досвід. Як магазин сантехніки ми не зупиняємося на перевірених товари. Ми також надаємо професійні консультації та комплексне обслуговування для індивідуальних клієнтів і компаній. Ми хочемо, щоб ви залишилися задоволені, тому робимо все, щоб наша пропозиція була для вас вигідним як за якістю, так і за ціною.\n
Запрошуємо до співпраці гуртових покупців та монтажників з усіх міст України. Спеціальні  знижки оптового клієнта, а також широкий асортимент якісного обладнання ТМ Aquatica, Leo, Dongyin, Wetron, і зручна взаємодія з нашими фахівцями доставить вам виключно позитивні емоції від співпраці.\n
Для наших клієнтів і партнерів ми хочемо бути вибором №1 в будь-який час. Наші комунікації побудовані на підтримці, умінні прислухатись та повазі.\n
Ми пропонуємо своїм партнерам лояльні умови та взаємовигідну співпрацю, якісне обслуговування, що включає у себе супровід на усіх етапах: від консультативної допомоги у виборі товарів до доставки безпосередньо на вашу адресу(в межах Дніпропетровської області) та транспортними компаніями на території України.\n
Весь реалізований нашою компанією товар, забезпечений терміном гарантійної підтримки. А також TECHBAZA сервіс забезпечує професійне гарантійне і післягарантійне сервісне обслуговування, яке включає в себе весь спектр можливих робіт.\n
Для кожного партнера ми підбираємо оптимальні умови співпраці.
Для торговельних організацій, "Інтернет-магазинів" та роздрібних "торгівельних точок" ми пропонуємо:
· Високий рівень якості продукції та "впізнаваності" бренду.
· Високу маржинальність та конкурентну ціну на ринку України.
· Оперативність у виконанні замовлень завдяки постійній наявності на складі.
· Швидкий зворотний зв'язок. Ми знаємо та розуміємо цінність вашого часу, тому оперативно опрацьовуємо ваші замовлення.
· Гнучку систему оплати та умови співпраці.\n
Запрошуємо вас ознайомитися з нашим асортиментом та сподіваємося на плідну співпрацю, а краще одразу телефонуйте: 
+380000000000
+380000000000
+380000000000,''', reply_markup=get_callback_button(btns={'Назад': 'back_company', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)


@regular_users_router.callback_query(F.data.in_(['button_optprice', 'button_pumpcal', 'button_feedback',
                                                 'button_insurance', 'button_ai']))
async def bot_info_buttons(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == 'button_optprice':
        await callback.message.answer('''OptPrice --> Індивідуальні оптові ціни\n
Функція «Індивідуальні оптові ціни» надає оптовим клієнтам зручний доступ до спеціального каталогу товарів із їхньою індивідуальною знижкою. Для входу вам потрібно ввести унікальний код, виданий під час співпраці. Якщо код правильний, бот підтвердить авторизацію та запропонує вибрати категорію товарів (наприклад, насоси чи сантехніка).\n
Потім ви вводите артикул потрібного товару, і якщо він є в каталозі, отримуєте детальну картку з фото (за наявності), коротким описом, базовою ціною та спеціальною ціною для вашої оптової категорії. Якщо товар відсутній, бот повідомить про це.\n
Завдяки такому формату кожен клієнт бачить лише свої умови ціноутворення, що забезпечує конфіденційність. Система автоматично оновлює дані про вартість і доступні товари, тож ви завжди бачите актуальну інформацію. У разі виникнення будь-яких проблем чи помилок, будь ласка, повідомте про них адміністратору бота через кнопку «Зворотний зв’язок».''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_bot', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'button_pumpcal':
        await callback.message.answer('''PumpCal  --> Розрахунок системи поливу\n
Функція «Розрахунок системи поливу» дає змогу розрахувати витрати води для крапельного поливу за заданими параметрами поля та самої системи зрошення. Ви вказуєте площу поля, відстань між рядами, крок емітера та водовилив одного емітера, а бот підкаже, скільки приблизно капельної стрічки вам потрібно та який буде загальний розхід води на годину. Це допоможе визначити, чи вистачить потужності поточного насоса або, за необхідності, підібрати іншу модель з урахуванням можливих втрат тиску.\n
1. Площа поля (A)
Вводиться в зручних для вас одиницях — сотки, гектари чи квадратні метри. Бот автоматично перераховує все у квадратні метри для подальших обчислень.\n
2. Відстань між рядами (S)
Це проміжок між сусідніми рядками, де прокладається крапельна стрічка.\n
3. Крок емітера (E)
Визначає, на якій відстані один від одного розташовані отвори (емітери) у стрічці. Від цього залежить рівномірність поливу й загальний витрата води.\n
4. Водовилив одного емітера (Q)
Показує, скільки води (л/год) подає кожен окремий емітер.\n
На основі цих показників бот розраховує:\n
•Загальну довжину капельної стрічки, яка знадобиться для поливу всіх рядків.
•Загальну кількість емитерів, щоб оцінити густоту системи та загальний розхід.
•Загальний розхід води (л/год чи м³/год), необхідний для роботи системи поливу.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_bot', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'button_feedback':
        await callback.message.answer('''Feedback --> Зворотний зв’язок\n
Кнопка «Зворотний зв’язок» дає змогу швидко надіслати своє повідомлення потрібній людині:\n
•Керівнику (з питань співпраці),
•Менеджеру (з інших питань),
•Адміністратору бота (з технічних питань роботи бота).\n
При натисканні цієї кнопки ви вибираєте одержувача, потім вводите ваш текст запиту. Повідомлення разом із контактними даними автоматично надсилається потрібній особі. Якщо необхідно, вона відповість вам особисто чи зв’яжеться іншим зручним способом.''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_bot', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'button_insurance':
        await callback.message.answer('''Моя страховка --> Моє страхування\n
Кнопка «Моє страхування» дає змогу швидко отримати інформацію про всі ваші діючі поліси в одному місці. Спочатку бот попросить вас надіслати свій номер телефону для ідентифікації.\n
Якщо все гаразд, ви побачите перелік актуальних страховок, включно з назвою транспортного засобу та номером поліса. Потім, обравши потрібний поліс, отримаєте детальну інформацію: дані страхувальника, дату початку та закінчення дії договору, номер реєстру та скільки днів залишилося до кінця дії поліса.\n''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_bot', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)

    if callback.data == 'button_ai':
        await callback.message.answer('''AI --> Інтелектуальний помічник TechBaza\n
Кнопка « Інтелектуальний помічник TechBaza» — це ваш персональний «розумний помічник», якого ми навчили на основі наших каталогів товарів. Якщо ви не дуже розбираєтеся в технічних тонкощах, не хвилюйтеся: достатньо просто ввести назву товару, модель чи запит, і бот спробує швидко знайти потрібну інформацію, спираючись на вже «вивчені» дані.\n
1. Як це працює?\n
Бот був заздалегідь «натренований» на нашій базі товарів і знає їхні характеристики, тому він може відповідати на ваші запитання або рекомендувати найкращий варіант.\n
2. Що потрібно від вас?\n
Просто запитайте: «Мені потрібен насос із такими-то властивостями» або «Яка сантехніка підійде для мого проєкту?» — і бот надасть список підходящих рішень чи детальну інформацію про товар.\n''',
                                      reply_markup=get_callback_button(btns={'Назад': 'back_bot', 'На головну': 'main_regular_user'}))
        await state.set_state(Info.main_process)


@regular_users_router.message(Command('get_id'))
async def about_us(message: Message):
    await message.answer(str(message.chat.id))


########################################################################################################################
################################################ ОПТОВА ТОРГІВЛЯ #######################################################
########################################################################################################################
class OptPrice(StatesGroup):
    group_client = None
    unique_code = None
    item_type = None

    authorization_step = State()
    choose_items = State()
    enter_sku = State()


@regular_users_router.message(F.text == 'Індивідуальні оптові ціни')
async def client_authorization(message: Message, state: FSMContext):
    await message.answer('Введіть код авторизації: ', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OptPrice.authorization_step)


async def get_user_group(unique_code: int):
    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            for group, table in {'A': 'users_a', 'B': 'users_b', 'C': 'users_c'}.items():
                await cur.execute(f'SELECT name FROM {table} WHERE unique_code = %s;', (unique_code,))
                user = await cur.fetchone()
                if user:
                    return user[0], group
    return None, None

async def send_welcome_message(entity, user_name, group, state):
    await entity.answer(f'Вітаємо, {user_name}:\n\n'
                        f'Оберіть категорію товарів:', reply_markup=get_callback_button(
        btns={'Насоси': 'pumps', 'Сантехніка': 'plumbing', 'С/Г інвентар': 'garden_inventory'}, sizes=(1,)))
    await state.update_data(group_client=group)
    await state.set_state(OptPrice.choose_items)


@regular_users_router.message(F.text.regexp(r'^\d{5,9}$'), StateFilter(OptPrice.authorization_step)) #Хендлер для обработки уникального кода пользователя
async def successful_authorization(message: Message, state: FSMContext):
    unique_code = int(message.text)
    await state.update_data(unique_code=unique_code)
    user_name, group = await get_user_group(unique_code)
    if user_name:
        await send_welcome_message(message, user_name, group, state)
    else:
        await message.answer('❌ Користувача немає в базі даних', reply_markup=get_callback_button(
            btns={'На головну': 'main_regular_user'}))


@regular_users_router.callback_query(F.data.in_({'choose_another_item', 'another_category'}))
async def handle_category_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    unique_code = data['unique_code']
    user_name, group = await get_user_group(unique_code)
    if user_name:
        await send_welcome_message(callback.message, user_name, group, state)
    else:
        await callback.message.answer('❌ Користувача немає в базі даних', reply_markup=get_callback_button(
            btns={'На головну': 'main_regular_user'}))


@regular_users_router.message(StateFilter(OptPrice.authorization_step))
async def problem_message(message: Message, state: FSMContext):
    await message.answer('❗ Не правильно введений код авторизації\n\n'
                         '📌 Введіть код авторизації заново: ')
    await state.set_state(OptPrice.authorization_step)


@regular_users_router.callback_query(F.data, StateFilter(OptPrice.choose_items))
async def enter_sku(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == 'pumps':
        await state.update_data(item_type=callback.data)
        await callback.message.answer('Введіть артикул насоса: \n',
                                      reply_markup=get_callback_button(
                                          btns={'Інша категорія': 'another_category'}
                                      ))
        await state.set_state(OptPrice.enter_sku)
    elif callback.data == 'plumbing':
        await state.update_data(item_type=callback.data)
        await callback.message.answer('Введіть артикул сантехніки: \n',
                                      reply_markup=get_callback_button(
                                          btns={'Інша категорія': 'another_category'}
                                      ))
        await state.set_state(OptPrice.enter_sku)
    elif callback.data == 'garden_inventory':
        await state.update_data(item_type=callback.data)
        await callback.message.answer('Введіть артикул садового інструменту: \n',
                                      reply_markup=get_callback_button(
                                          btns={'Інша категорія': 'another_category'}
                                      ))
        await state.set_state(OptPrice.enter_sku)


@regular_users_router.message(StateFilter(OptPrice.choose_items))
async def problem_choosing_items(message: Message, state: FSMContext):
    await message.answer('Оберіть кнопку!', reply_markup=get_callback_button(
        btns={'Насоси': 'pumps', 'Сантехніка': 'plumbing', 'С/Г інвентар': 'garden_inventory'},
        sizes=(1,)))
    await state.set_state(OptPrice.choose_items)


@regular_users_router.message(F.text, StateFilter(OptPrice.enter_sku))
async def finding_sku(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    group_client = data.get('group_client')

    sku = message.text.strip()

    async with await get_connection(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db_name=os.getenv('db_name')
    ) as conn:
        async with conn.cursor() as cur:
            result = None
            for table in ['pumps', 'plumbing', 'garden_inventory']:
                await cur.execute(f'SELECT photo, sku, name, brand, basic_price, in_one_pack, link, discount FROM {table} WHERE sku = %s;', (sku,))
                result = await cur.fetchone()
                if result:
                    break

            if not result:
                await message.answer(
                    "❌ Товар за артикулом не знайдено\n\n"
                    "👇 Введіть артикул заново: ",
                    reply_markup=get_callback_button(
                        btns={'Інша категорія': 'another_category'}
                    )
                )
                return

            await cur.execute('SELECT actual_course FROM actual_course;')
            actual_course = await cur.fetchone()
            actual_course = actual_course[0]

            photo, sku, name, brand, basic_price, in_one_pack, link, discount = result
            discount_for_categories = discount.split('|')
            A, B, C = map(float, discount_for_categories)

            discounted_price = 0

            basic_price_decimal = Decimal(str(basic_price)) * actual_course

            #Decimal(str(basic_price)) — используется для точных вычислений, чтобы избежать проблем с округлением

            if group_client == 'A':
                discounted_price = basic_price_decimal - (basic_price_decimal * Decimal(A))
            elif group_client == 'B':
                discounted_price = basic_price_decimal - (basic_price_decimal * Decimal(B))
            elif group_client == 'C':
                discounted_price = basic_price_decimal - (basic_price_decimal * Decimal(C))

            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=(
                    f'<b>Товар</b>: {name}\n'
                    f'<b>Бренд</b>: {brand}\n'
                    f'<b>Базова ціна</b>: {round(basic_price * actual_course, 2)} грн.\n'
                    f'<b>Оптова ціна</b>: {round(discounted_price, 2)} грн.\n'
                    f'<b>В одній коробці</b>: {in_one_pack}\n'
                    f'<b>Посилання</b>: {link}\n\n'
                    f"<b>Для замовлення зв’яжіться за номерами</b>:\n"
                    f"{os.getenv('HEAD_PHONE')}\n"
                    f"{os.getenv('SUPERVISOR_PHONE')}\n"
                    f"{os.getenv('SELLER_PHONE')}"
                ),
                reply_markup=get_callback_button(
                    btns={'Інший товар': 'choose_another_item', 'На головну': 'main_regular_user'}
                )
            )

            await state.set_state(OptPrice.authorization_step)


########################################################################################################################
############################################### МОЄ СТРАХУВАННЯ ########################################################
########################################################################################################################
class MyInsurance(StatesGroup):
    requested_phone_number = State()
    choose_car = State()


@regular_users_router.message(F.text == 'Моє страхування')
async def send_phone_number(message: Message, state: FSMContext):
    await message.answer(
        '<b>👇 Надішліть свій номер телефону: </b>',
        reply_markup=get_keyboard(btns=['Надіслати номер'], request_contact=[0])
    )
    await state.set_state(MyInsurance.requested_phone_number)


@regular_users_router.message(F.contact, StateFilter(MyInsurance.requested_phone_number))
async def send_insurance_info(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number.lstrip('+')
    phone_number = phone_number[2:]

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id, vehicle, license_plate FROM insurance WHERE phone_number = %s;',
                              (phone_number,))
            result = await cur.fetchall()
            if result:
                insurance_dict = {res[1]: str(res[0]) for res in result}
                insurance_message = '\n'.join([f'🔹 {str(res[1])}: {str(res[2])}' for res in result])
                await message.answer('<b>Діючі страхові поліси</b>:\n', reply_markup=types.ReplyKeyboardRemove())
                await message.answer(f'{insurance_message}\n')
                await message.answer(
                    f'👇 <b>Щоб переглянути повну інформацію по полісам, оберіть транспортний засіб</b>',
                    reply_markup=get_callback_button(btns=insurance_dict))
                await state.set_state(MyInsurance.choose_car)
            else:
                await message.answer('❌ За вашим номером не знайдено жодного страхового поліса',
                                     reply_markup=get_callback_button(
                                         btns={'На головну': 'main_regular_user'}
                                     ))
                await state.clear()


@regular_users_router.callback_query(F.data, StateFilter(MyInsurance.choose_car))
async def choose_car_for_full_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    insurance_id = int(callback.data)

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT vehicle, license_plate, full_name, from_date, to_date '
                              'FROM insurance WHERE id = %s;', (int(insurance_id),))
            result = await cur.fetchone()
            await cur.execute("""
                SELECT DATEDIFF(STR_TO_DATE(to_date, %s), CURDATE()) AS days_remaining
                FROM insurance
                WHERE id = %s;
            """, ('%Y-%m-%d', insurance_id))
            day_remain = await cur.fetchone()
            if result and day_remain:
                vehicle, license_plate, full_name, from_date, to_date = result

                if day_remain[0] < 0:
                    status_message = "❌ Поліс ПРОСТРОЧЕНО!"
                else:
                    status_message = f'До кінця дії полісу залишилось: {day_remain[0]} днів.'

                await callback.message.answer('👇 <b>Інформація по полісу:</b>\n\n'
                                              f'🔹 Страхувальник: {full_name}\n\n'
                                              f'🔹 Т/з: {vehicle}\n'
                                              f'🔹 Реєстр. номер: {license_plate}\n\n'
                                              f'🔹 З: {from_date}\n'
                                              f'🔹 По: {to_date}\n\n'
                                              f'{status_message}',
                                              reply_markup=get_callback_button(
                                                  btns={'На головну': 'main_regular_user'}
                                              ))
            else:
                await callback.message.answer('❌ При виконанні запиту виникла помилка, спробуйте ще раз',
                                              reply_markup=START_BUTTONS)
    await state.clear()
########################################################################################################################
########################################################################################################################
########################################################################################################################
class AIMessage(StatesGroup):
    start_conversation = State()
    handling_callbacks = State()


@regular_users_router.message(F.text == 'Інтелектуальний помічник TechBaza')
async def start_ai_conversation(message: Message, state: FSMContext):
    await message.answer('👇 Введіть ваше запитання: ')
    await state.set_state(AIMessage.start_conversation)


@regular_users_router.message(F.text, StateFilter(AIMessage.start_conversation))
async def response(message: Message, state: FSMContext):
    user_message = message.text.strip()

    if len(user_message) > 1500:
        await message.answer("⚠️ Ваш запит трохи завеликий! Максимум 1500 символів 😉")
        return

    await message.answer("🔍 Обробляю інформацію...")

    try:
        ai_response = await get_ai_response(user_message)

        await message.answer(
            ai_response,
            reply_markup=get_callback_button(btns={'Завершити': 'end_conversation'})
        )

        await state.set_state(AIMessage.start_conversation)

    except Exception as e:
        print(f"AI error: {e}")

        await message.answer(
            "⚠️ Вибачте, сталася технічна проблема. Спробуйте ще раз трохи пізніше або зверніться до підтримки TechBaza. 🛠",
            reply_markup=START_BUTTONS
        )
        await state.clear()


@regular_users_router.callback_query(F.data == 'end_conversation', StateFilter(AIMessage.start_conversation))
async def handling_callbacks(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == 'end_conversation':
        await callback.message.answer('😊 Радий був допомогти!', reply_markup=START_BUTTONS)
        await state.clear()



########################################################################################################################
########################################################################################################################
########################################################################################################################
@regular_users_router.message(Command('get_id'))
async def get_id(message: Message):
    await message.answer(str(message.chat.id))



@regular_users_router.message(F.text, StateFilter('*'))
async def general_problem(message: Message, state: FSMContext):
    if message.text == '/admin':
        await message.answer('❌ Ви не адміністратор', reply_markup=START_BUTTONS)
    else:
        await message.answer('Неправильний тип даних!', reply_markup=START_BUTTONS)
    await state.clear()



