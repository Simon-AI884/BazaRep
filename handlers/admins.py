import os
import re

from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from database.connection import get_connection
from filters.chat_type_filter import ChatTypeFilter
from filters.is_admin import IsAdmin
from keyboards.inline_keyboards import get_callback_button
from keyboards.reply_keyboards import get_keyboard

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']), IsAdmin())

ADMIN_REPLY_KB = get_keyboard(
    btns=['Змінити курс', 'Страхування', 'Додати/Змінити товар', 'Додати/Видалити користувача'],
    sizes=(2, 1, 1))


@admin_router.message(Command('admin'))
async def admin_start(message: Message, state: FSMContext):
    await message.answer('Ви авторизувались, як <b>адміністратор</b>',
                         reply_markup=ADMIN_REPLY_KB)
    await state.clear()


@admin_router.callback_query(F.data == 'main', StateFilter('*'))
async def general_callback_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Ви повернулись на головну сторінку.\n',
                                  reply_markup=ADMIN_REPLY_KB)
    await state.clear()


########################################################################################################################
############################################## ЗМІНИТИ КУРС ############################################################
########################################################################################################################
class ChangeCourse(StatesGroup):
    if_course = None

    change_course_start = State()
    change_course_end = State()


@admin_router.message(F.text == 'Змінити курс')
async def change_course_start(message: Message, state: FSMContext):
    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT actual_course FROM actual_course;')
            actual_course = await cur.fetchone()

            if actual_course:
                await message.answer(f'Актуальний курс: '
                                     f'<b>1$ = {actual_course[0]} грн.</b>',
                                     reply_markup=get_callback_button(
                                         btns={'На головну': 'main', 'Ввести курс': 'enter_course'}))
                await state.update_data(if_course=True)
                await state.set_state(ChangeCourse.change_course_start)
            if not actual_course:
                await message.answer('Актуального курсу не знайдено.',
                                     reply_markup=get_callback_button(
                                         btns={'Ввести курс': 'enter_course'}
                                     ))
                await state.update_data(if_course=False)
                await state.set_state(ChangeCourse.change_course_start)


@admin_router.callback_query(F.data == 'enter_course', StateFilter(ChangeCourse.change_course_start))
async def change_course_continue(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введіть новий курс:\n'
                                  'Правильний формат: XX.YYY', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(ChangeCourse.change_course_end)


@admin_router.message(F.text.regexp(r'^\d{2,3}\.\d{2,3}$'), StateFilter(ChangeCourse.change_course_end))
async def change_course_final(message: Message, state: FSMContext):
    try:
        actual_course = float(message.text)
    except Exception as e:
        print('Problem with course!')

    data = await state.get_data()
    if_course = data['if_course']

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            if if_course:
                await cur.execute('UPDATE actual_course SET actual_course = %s;', (actual_course,))
                await conn.commit()
            if not if_course:
                await cur.execute('INSERT INTO actual_course (actual_course) '
                                  'VALUES (%s) ON DUPLICATE KEY UPDATE actual_course=actual_course;', (actual_course,))
                await conn.commit()

    await message.answer('✅ Курс змінено успішно!', reply_markup=ADMIN_REPLY_KB)
    await state.clear()


########################################################################################################################
######################################## ДОДАТИ/ЗМІНИТИ ТОВАР ##########################################################
########################################################################################################################
class AddChangeItem(StatesGroup):
    type = None
    id = None
    sku = None
    discount = None

    item_for_change = {}

    choose_item = State()

    enter_sku = State()

    enter_photo = State()
    enter_new_sku = State()
    enter_name = State()
    enter_brand = State()
    enter_basic_price = State()
    enter_in_one_pack = State()
    enter_link = State()
    enter_special_category = State()


@admin_router.message(F.text == 'Додати/Змінити товар')
async def add_change_item_start(message: Message, state: FSMContext):
    await message.answer('👇 <b>Оберіть тип товару</b>: ', reply_markup=get_callback_button(
        btns={'Насос': 'pump', 'Сантехніка': 'plumbing', 'С/Г інвентар': 'garden_inventory'}, sizes=(1,)
    ))
    await state.set_state(AddChangeItem.choose_item)


@admin_router.callback_query(F.data.in_(['pump', 'plumbing', 'garden_inventory']),
                             StateFilter(AddChangeItem.choose_item))
async def add_change_item_choose_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(type=callback.data)
    await callback.message.answer('👇 <b>Введіть артикул товару</b>\n'
                                  '<i>Якщо бажаєте додати товар, введіть "000"</i>',
                                  reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddChangeItem.enter_sku)


@admin_router.message(F.text == '000', StateFilter(AddChangeItem.enter_sku))
async def adding_sku(message: Message, state: FSMContext):
    await message.answer('👇 <b>Відправте нове фото товару</b>: ', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddChangeItem.enter_photo)


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_sku))
async def add_change_item_find_by_sku(message: Message, state: FSMContext):
    sku = message.text.strip()
    data = await state.get_data()
    item_type = data.get('type')

    table = {
        'pump': 'pumps',
        'plumbing': 'plumbing',
        'garden_inventory': 'garden_inventory'
    }.get(item_type)

    if table is None:
        await message.answer("Невірний тип товару.", reply_markup=ADMIN_REPLY_KB)
        return

    async with await get_connection(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db_name=os.getenv('db_name')
    ) as conn:
        async with conn.cursor() as cur:
            if table in ['pumps', 'plumbing']:
                await cur.execute(f'''
                    SELECT id, photo, sku, name, brand, basic_price, in_one_pack, link, discount 
                    FROM {table} WHERE sku = %s;
                ''', (sku,))
            else:
                await cur.execute('''
                    SELECT id, photo, sku, name, brand, basic_price, in_one_pack, special_category, link, discount 
                    FROM garden_inventory WHERE sku = %s;
                ''', (sku,))

            item = await cur.fetchone()

            if item:
                if table == 'garden_inventory':
                    id, photo, sku, name, brand, basic_price, in_one_pack, special_category, link, discount = item
                else:
                    id, photo, sku, name, brand, basic_price, in_one_pack, link, discount = item
                    special_category = None

                response = (
                        f"<b>Назва</b>: {name}\n"
                        f"<b>Марка</b>: {brand}\n"
                        f"<b>Базова ціна</b>: {basic_price} $\n"
                        f"<b>У одній пачці</b>: {in_one_pack}\n"
                        + (f"<b>Спеціальна категорія</b>: {special_category}\n" if special_category else "") +
                        f"<b>Посилання</b>: {link}\n"
                        f"<b>Знижки</b>: {discount}"
                )

                keyboard = get_callback_button(btns={
                    'Видалити': f'delete_{id}',
                    'Змінити': f'edit_{id}',
                    'На головну': 'main'
                })

                if photo:
                    await message.answer_photo(photo=photo, caption=response, reply_markup=keyboard)
                else:
                    await message.answer(response, reply_markup=keyboard)
            else:
                await message.answer("❌ Товар за артикулом не знайдено.", reply_markup=ADMIN_REPLY_KB)


@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_product(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_type = data.get('type')

    product_id = callback.data.split('_')[-1]

    async with await get_connection(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db_name=os.getenv('db_name')
    ) as conn:
        async with conn.cursor() as cur:
            table = 'pumps' if item_type == 'pump' else 'plumbing' if item_type == 'plumbing' else 'garden_inventory'
            await cur.execute(f'DELETE FROM {table} WHERE id = %s;', (product_id,))
            await conn.commit()
        await callback.answer()
        await callback.message.answer('✅ Товар успішно видалено!', reply_markup=ADMIN_REPLY_KB)
        await state.clear()


@admin_router.callback_query(F.data.startswith('edit_'))
async def delete_product(callback: types.CallbackQuery, state: FSMContext):
    product_id = callback.data.split('_')[-1]
    await state.update_data(id=product_id)

    data = await state.get_data()
    item_type = data.get('type')

    async with await get_connection(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db_name=os.getenv('db_name')
    ) as conn:
        try:
            async with conn.cursor() as cur:
                table = 'pumps' if item_type == 'pump' else 'plumbing' if item_type == 'plumbing' else 'garden_inventory'
                if table == 'pumps' or table == 'plumbing':
                    await cur.execute(f'SELECT id, photo, sku, name, brand, basic_price, in_one_pack, link, discount '
                                      f'FROM {table} WHERE id = %s;',
                                      (product_id,))
                    row = await cur.fetchone()
                if table == 'garden_inventory':
                    await cur.execute(
                        f'SELECT id, photo, sku, name, brand, basic_price, in_one_pack, special_category, link, discount '
                        f'FROM garden_inventory WHERE id = %s;',
                        (product_id,))
                    row = await cur.fetchone()
                column_names = [desc[0] for desc in cur.description]
                column_names = [name for name in column_names if name]
                AddChangeItem.item_for_change = dict(zip(column_names, row))
                print(str(AddChangeItem.item_for_change))
        except Exception as e:
            print(f"Error inserting data: {e}")
        finally:
            conn.close()
        await callback.answer()
        await callback.message.answer('👇 <b>Відправте нове фото товару</b>: ', reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AddChangeItem.enter_photo)


@admin_router.message(or_f(F.photo, F.text == '.'), StateFilter(AddChangeItem.enter_photo))
async def add_photo(message: Message, state: FSMContext):
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_photo=AddChangeItem.item_for_change['photo'])
    else:
        await state.update_data(enter_photo=message.photo[-1].file_id)

    await message.answer('👇 <b>Введіть новий артикул товару</b>: ')
    await state.set_state(AddChangeItem.enter_new_sku)


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_new_sku))
async def add_sku(message: Message, state: FSMContext):
    if len(message.text) > 15:
        await message.answer('👇 <b>Введіть артикул товару заново</b>: \n\n'
                             '<i>Не більше 15 символів</i>')
        return
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_sku=AddChangeItem.item_for_change['sku'])
    else:
        await state.update_data(enter_sku=message.text)

    await message.answer('👇 <b>Введіть нову назву товару</b>: ')
    await state.set_state(AddChangeItem.enter_name)


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_name))
async def add_sku(message: Message, state: FSMContext):
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_name=AddChangeItem.item_for_change['name'])
    else:
        await state.update_data(enter_name=message.text)

    await message.answer('👇 <b>Введіть нову марку товару</b>: ')
    await state.set_state(AddChangeItem.enter_brand)


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_brand))
async def add_sku(message: Message, state: FSMContext):
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_brand=AddChangeItem.item_for_change['brand'])
    else:
        await state.update_data(enter_brand=message.text)

    await message.answer('👇 <b>Введіть базову ціну товару</b>\n'
                         '<i>Формат XXXX.YYY</i> ')
    await state.set_state(AddChangeItem.enter_basic_price)


@admin_router.message(or_f(F.text.regexp(r'^\d{1,4}\.\d{1,3}$'), F.text == '.'),
                      StateFilter(AddChangeItem.enter_basic_price))
async def add_sku(message: Message, state: FSMContext):
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_basic_price=AddChangeItem.item_for_change['basic_price'])
    else:
        await state.update_data(enter_basic_price=message.text)

    await message.answer('👇 <b>Введіть кількість одиниць в одній упаковці</b>: ')
    await state.set_state(AddChangeItem.enter_in_one_pack)


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_in_one_pack))
async def add_sku(message: Message, state: FSMContext):
    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_in_one_pack=AddChangeItem.item_for_change['in_one_pack'])
    else:
        await state.update_data(enter_in_one_pack=message.text)

    data = await state.get_data()
    if data['type'] == 'garden_inventory':
        await message.answer('👇 <b>Оберіть категорію</b>: ',
                             reply_markup=get_callback_button(
                                 btns={'Хомуты': 'clamps',
                                       'ЗІЗ-рукави': 'ziz_sleeves',
                                       'Інвентар для поливу і оприскування': 'watery_spraying',
                                       'Інвентар для догляду за деревами, кущами і газоном': 'tree_care',
                                       'Інвентар для роботи з ґрунтом': 'soil_care',
                                       'Драбини, стрем’янки': 'ladders',
                                       'Тачки, візки, комплектуючі': 'carts',
                                       'Електричні інструменти та обладнання': 'electric_tools',
                                       'Садовий електроінструмент': 'garden_power_tools',
                                       'Бензомоторні інструменти та обладнання': 'gasoline_powered',
                                       'Генератори та комплектуючі': 'generators',
                                       'Зварювальне обладнання': 'welding_inventory'}
                             ))
        await state.set_state(AddChangeItem.enter_special_category)
    else:
        await message.answer('👇 <b>Відправте нове посилання</b>: ')
        await state.set_state(AddChangeItem.enter_link)


@admin_router.callback_query(F.data, StateFilter(AddChangeItem.enter_special_category))
async def enter_special_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(enter_special_category=callback.data)
    await callback.message.answer('👇 <b>Відправте нове посилання</b>: ', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddChangeItem.enter_link)


@admin_router.message(F.text == '.', StateFilter(AddChangeItem.enter_special_category))
async def enter_special_category(message: Message, state: FSMContext):
    await state.update_data(enter_special_category=AddChangeItem.item_for_change['enter_category'])
    await message.answer('👇 <b>Відправте нове посилання</b>: ')
    await state.set_state(AddChangeItem.enter_link)


async def get_table_name(item_type):
    return {
        'pump': 'pumps',
        'plumbing': 'plumbing',
        'garden_inventory': 'garden_inventory'
    }.get(item_type, 'garden_inventory')


async def get_discount(item_type, category):
    discounts = {
        'pump': '0.33|0.3|0.27',
        'plumbing': '0.42|0.4|0.38',
        'garden_inventory': {
            'watery_spraying': '0.33|0.3|0.27',
            'tree_care': '0.33|0.3|0.27',
            'soil_care': '0.33|0.3|0.27',
            'ladders': '0.33|0.3|0.27',
            'carts': '0.33|0.3|0.27',
            'electric_tools': '0.33|0.3|0.27',
            'garden_power_tools': '0.33|0.3|0.27',
            'gasoline_powered': '0.33|0.3|0.27',
            'generators': '0.33|0.3|0.27',
            'clamps': '0.3|0.25|0.23',
            'ziz_sleeves': '0.3|0.27|0.25',
            'welding_inventory': '0.3|0.27|0.23'
        }
    }
    return discounts.get(item_type, {}).get(category, None) if isinstance(discounts.get(item_type), dict) else discounts.get(item_type)


async def translate_category(category):
    categories = {
        'clamps': 'Хомути',
        'ziz_sleeves': 'ЗІЗ-рукави',
        'watery_spraying': 'Інвентар для поливу і оприскування',
        'tree_care': 'Інвентар для догляду за деревами, кущами і газоном',
        'soil_care': 'Інвентар для роботи з ґрунтом',
        'ladders': 'Драбини, стрем’янки',
        'carts': 'Тачки, візки, комплектуючі',
        'electric_tools': 'Електричні інструменти і обладнання',
        'garden_power_tools': 'Садовий електроінструмент',
        'gasoline_powered': 'Бензомоторні інструменти та обладнання',
        'generators': 'Генератори та комплектуючи',
        'welding_inventory': 'Зварювальне обладнання'
    }
    return categories.get(category, category)


async def update_or_insert_item(data, table, conn):
    async with conn.cursor() as cur:
        if AddChangeItem.item_for_change:
            query = f'''
                UPDATE {table} 
                SET photo = %s, sku = %s, name = %s, brand = %s, basic_price = %s, 
                    in_one_pack = %s, link = %s, discount = %s {', special_category = %s' if table == 'garden_inventory' else ''}
                WHERE id = %s;
            '''
            values = (
                data['enter_photo'], data['enter_sku'], data['enter_name'], data['enter_brand'],
                data['enter_basic_price'], data['enter_in_one_pack'], data['enter_link'], data['discount']
            )
            if table == 'garden_inventory':
                values += (data['enter_special_category'],)
            values += (data['id'],)

        else:
            query = f'''
                INSERT INTO {table} (photo, sku, name, brand, basic_price, in_one_pack, link, discount
                {', special_category' if table == 'garden_inventory' else ''})
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s {', %s' if table == 'garden_inventory' else ''});
            '''
            values = (
                data['enter_photo'], data['enter_sku'], data['enter_name'], data['enter_brand'],
                data['enter_basic_price'], data['enter_in_one_pack'], data['enter_link'], data['discount']
            )
            if table == 'garden_inventory':
                values += (data['enter_special_category'],)

        await cur.execute(query, values)
        await conn.commit()


@admin_router.message(F.text, StateFilter(AddChangeItem.enter_link))
async def add_sku(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text == '.' and AddChangeItem.item_for_change:
        await state.update_data(enter_link=AddChangeItem.item_for_change['link'])
    else:
        await state.update_data(enter_link=message.text)

    data = await state.get_data()
    discount = await get_discount(data['type'], data.get('enter_special_category'))
    if discount:
        await state.update_data(discount=discount)

    if 'enter_special_category' in data:
        await state.update_data(enter_special_category=await translate_category(data['enter_special_category']))

    async with await get_connection(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db_name=os.getenv('db_name')
    ) as conn:
        table = await get_table_name(data['type'])
        await update_or_insert_item(await state.get_data(), table, conn)

    await message.answer(
        '✅ <b>Товар успішно оновлено!</b>' if AddChangeItem.item_for_change else '✅ <b>Новий товар успішно додано!</b>',
        reply_markup=ADMIN_REPLY_KB
    )

    await state.clear()
    AddChangeItem.item_for_change = None


########################################################################################################################
############################################ ДОДАТИ/ЗМІНИТИ КОРИСТУВАЧА ################################################
########################################################################################################################
class AddDeleteUser(StatesGroup):
    process = None
    unique_code = None
    user_category = None

    main_process = State()
    choose_user_category = State()

    deleting_process = State()
    enter_name = State()


@admin_router.message(F.text == 'Додати/Видалити користувача')
async def add_delete_user_start(message: Message, state: FSMContext):
    await message.answer('👇 <b>Оберіть дію:</b> ', reply_markup=get_callback_button(
        btns={'Додати': 'user_add', 'Видалити': 'user_delete'}
    ))
    await state.set_state(AddDeleteUser.main_process)


@admin_router.callback_query(F.data.in_(['user_add', 'user_delete']), StateFilter(AddDeleteUser.main_process))
async def choose_type_of_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('👇 <b>Введіть унікальний код користувача</b>: ',
                                  reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(process=callback.data)
    await state.set_state(AddDeleteUser.choose_user_category)


@admin_router.message(F.text, StateFilter(AddDeleteUser.choose_user_category))
async def continue_add_delete_process(message: Message, state: FSMContext):
    pattern = r'^\d{5,9}$'
    if re.fullmatch(pattern, message.text):
        await state.update_data(unique_code=message.text)
        data = await state.get_data()

        process = data['process']

        if process == 'user_add':
            await message.answer('👇 <b>Оберіть категорію користувача</b>: ', reply_markup=get_callback_button(
                btns={'A': 'A', 'B': 'B', 'C': 'C'}, sizes=(3,)
            ))
            await state.set_state(AddDeleteUser.deleting_process)

        elif process == 'user_delete':
            await message.answer('👇 <b>Оберіть категорію користувача для видалення</b>: ',
                                 reply_markup=get_callback_button(
                                     btns={'A': 'A', 'B': 'B', 'C': 'C'}, sizes=(3,)
                                 ))
            await state.set_state(AddDeleteUser.deleting_process)
    else:
        await message.answer('<b>❌ Неправильний тип даних</b>\n'
                             '👇 <b>Введіть унікальний код користувача заново</b>: ')
        return


@admin_router.callback_query(F.data.in_(['A', 'B', 'C']), StateFilter(AddDeleteUser.deleting_process))
async def deleting_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    process = data['process']
    unique_code = data['unique_code']
    user_category = callback.data

    if process == 'user_add':
        await state.update_data(user_category=user_category)
        await callback.message.answer("👇 <b>Введіть ім'я користувача</b>: ")
        await state.set_state(AddDeleteUser.enter_name)

    elif process == 'user_delete':
        async with await get_connection(host=os.getenv('host'),
                                        port=int(os.getenv('port')),
                                        user=os.getenv('user'),
                                        password=os.getenv('password'),
                                        db_name=os.getenv('db_name')) as conn:
            async with conn.cursor() as cur:
                table = f'users_{user_category}'
                await cur.execute(f'DELETE FROM {table} WHERE unique_code = %s;', (unique_code,))
                await conn.commit()
                await callback.message.answer('✅ <b>Користувача успішно видалено!</b>', reply_markup=ADMIN_REPLY_KB)
        await state.clear()


@admin_router.message(F.text, StateFilter(AddDeleteUser.enter_name))
async def adding_process(message: Message, state: FSMContext):
    name = message.text
    data = await state.get_data()
    unique_code = data['unique_code']
    user_category = data['user_category']

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            table = f'users_{user_category}'
            await cur.execute(f'INSERT INTO {table} (name, unique_code) '
                              f'VALUES (%s, %s);', (name, unique_code))
            await conn.commit()
            await message.answer('✅ <b>Користувача успішно додано!</b>', reply_markup=ADMIN_REPLY_KB)
    await state.clear()


########################################################################################################################
################################################## АДМІН-СТРАХУВАННЯ ###################################################
########################################################################################################################
class Insurance(StatesGroup):
    insurance_id = None

    enter_check_mobile_phone = State()

    enter_vehicle = State()
    enter_license_plate = State()
    enter_full_name = State()
    enter_from_date = State()
    enter_to_date = State()
    enter_phone_number = State()

    insurance_for_change = {}


@admin_router.message(F.text == 'Страхування')
async def start_insurance(message: Message, state: FSMContext):
    await message.answer('👇 <b>Введіть номер телефону страхувальника</b>\n'
                         '<i>Нова страховка - введіть "000"</i>', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Insurance.enter_check_mobile_phone)


@admin_router.message(or_f(F.text == '000', F.text.regexp(r'^0\d{9}$')),
                      StateFilter(Insurance.enter_check_mobile_phone))
async def main_process(message: Message, state: FSMContext):
    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM insurance WHERE phone_number = %s;', (message.text,))
            result = await cur.fetchone()
            if result:
                insurance_id, vehicle, license_plate, full_name, from_date, to_date, phone_number = result
                await message.answer('👇 <b>Актуальна інформація</b>:\n\n'
                                     f'Транспортний засіб: <b>{vehicle}</b>\n'
                                     f'Реєстраціний номер: <b>{license_plate}</b>\n'
                                     f'ПІБ: <b>{full_name}</b>\n'
                                     f'З: <b>{from_date}</b>\n'
                                     f'По: <b>{to_date}</b>\n'
                                     f'Номер телефону: <b>{phone_number}</b>\n\n', reply_markup=get_callback_button(
                    btns={'Змінити': f'insurance_change_{insurance_id}', 'Видалити': f'insurance_delete_{insurance_id}',
                          'На головну': 'main'}
                ))
                await state.update_data(insurance_id=insurance_id)
            if not result:
                if message.text == '000':
                    await message.answer('<b>Нова страховка</b>\n\n'
                                         '<b>👇 Введіть інформацію про транспортний засіб: </b>\n')
                    await state.set_state(Insurance.enter_vehicle)
                else:
                    await message.answer('<b>❌ Інформації за даним номером не знайдено</b>\n\n',
                                         reply_markup=ADMIN_REPLY_KB)
                    await state.clear()


@admin_router.callback_query(F.data.startswith('insurance_'))
async def delete_change_insurance_by_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    insurance_id = data['insurance_id']

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        async with conn.cursor() as cur:
            if callback.data.startswith('insurance_change_'):
                try:
                    await cur.execute(f'SELECT vehicle, license_plate, full_name, from_date, to_date, phone_number '
                                      f'FROM insurance WHERE id = %s;',
                                      (insurance_id,))
                    result = await cur.fetchone()
                    column_names = [desc[0] for desc in cur.description]
                    column_names = [name for name in column_names if name]
                    Insurance.insurance_for_change = dict(zip(column_names, result))
                except Exception as e:
                    print(f"Error inserting data: {e}")
                finally:
                    conn.close()
                await callback.message.answer('<b>👇 Введіть інформацію про транспортний засіб: </b>\n')
                await state.set_state(Insurance.enter_vehicle)

            if callback.data.startswith('insurance_delete_'):
                async with await get_connection(host=os.getenv('host'),
                                                port=int(os.getenv('port')),
                                                user=os.getenv('user'),
                                                password=os.getenv('password'),
                                                db_name=os.getenv('db_name')) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute('DELETE FROM insurance WHERE id = %s;', (insurance_id,))
                        await conn.commit()
                await callback.message.answer('✅ Інформацію про страховку було успішно видалено',
                                              reply_markup=ADMIN_REPLY_KB)
                await state.clear()


@admin_router.message(F.text, StateFilter(Insurance.enter_vehicle))
async def enter_vehicle_info(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_vehicle=Insurance.insurance_for_change['vehicle'])
    else:
        await state.update_data(enter_vehicle=message.text)
    await message.answer('<b>👇 Введіть реєстраційний номер транспортного засобу: </b>\n')
    await state.set_state(Insurance.enter_license_plate)


@admin_router.message(or_f(F.text.regexp(r'^[A-ZА-Я]{2}\d{4}[A-ZА-Я]{2}$'), F.text == '.'),
                      StateFilter(Insurance.enter_license_plate))
async def enter_license_plate(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_license_plate=Insurance.insurance_for_change['license_plate'])
    else:
        license_plate = ''.join([i if i in '0123456789' else i.upper() for i in message.text])
        await state.update_data(enter_license_plate=license_plate)
    await message.answer('<b>👇 Введіть ПІБ страхувальника: </b>\n')
    await state.set_state(Insurance.enter_full_name)


@admin_router.message(StateFilter(Insurance.enter_license_plate))
async def enter_license_plate_problem(message: Message):
    await message.answer('<b>👇 Введіть реєстраційний номер транспортного засобу: </b>\n'
                         '<i>Формат АА0000АА</i>')
    return


@admin_router.message(F.text, StateFilter(Insurance.enter_full_name))
async def enter_full_name(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_full_name=Insurance.insurance_for_change['full_name'])
    else:
        await state.update_data(enter_full_name=message.text)
    await message.answer('<b>👇 Введіть дату початку періоду страхування: </b>\n'
                         '<i>Формат YYYY-MM-DD</i>')
    await state.set_state(Insurance.enter_from_date)


@admin_router.message(or_f(F.text.regexp(r'^(?:([0-9]{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]))$'), F.text == '.'),
                      StateFilter(Insurance.enter_from_date))
async def enter_from_date(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_from_date=Insurance.insurance_for_change['from_date'])
    else:
        await state.update_data(enter_from_date=message.text)
    await message.answer('<b>👇 Введіть дату закінчення періоду страхування: </b>\n'
                         '<i>Формат YYYY-MM-DD</i>')
    await state.set_state(Insurance.enter_to_date)


@admin_router.message(StateFilter(Insurance.enter_from_date))
async def enter_from_date_problem(message: Message):
    await message.answer('<b>👇 Введіть дату початку періоду страхування: </b>\n'
                         '<i>Правильний формат YYYY-MM-DD</i>')
    return


@admin_router.message(or_f(F.text.regexp(r'^(?:([0-9]{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]))$'), F.text == '.'),
                      StateFilter(Insurance.enter_to_date))
async def enter_to_date(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_to_date=Insurance.insurance_for_change['to_date'])
    else:
        await state.update_data(enter_to_date=message.text)
    await message.answer('<b>👇 Введіть номер телефону страхувальника: </b>\n'
                         '<i>Формат 0000000000</i>')
    await state.set_state(Insurance.enter_phone_number)


@admin_router.message(StateFilter(Insurance.enter_to_date))
async def enter_to_date_problem(message: Message):
    await message.answer('<b>👇 Введіть дату закінчення періоду страхування: </b>\n'
                         '<i>Правильний формат YYYY-MM-DD</i>')
    return


@admin_router.message(or_f(F.text.regexp(r'^0\d{9}$'), F.text == '.'), StateFilter(Insurance.enter_phone_number))
async def enter_phone_number(message: Message, state: FSMContext):
    if message.text == '.' and Insurance.insurance_for_change:
        await state.update_data(enter_phone_number=Insurance.insurance_for_change['phone_number'])
    else:
        await state.update_data(enter_phone_number=message.text)

    data = await state.get_data()
    if Insurance.insurance_for_change:
        insurance_id = data['insurance_id']

    info_vehicle = data['enter_vehicle']
    license_plate = data['enter_license_plate']
    full_name = data['enter_full_name']
    from_date = data['enter_from_date']
    to_date = data['enter_to_date']
    phone_number = data['enter_phone_number']

    async with await get_connection(host=os.getenv('host'),
                                    port=int(os.getenv('port')),
                                    user=os.getenv('user'),
                                    password=os.getenv('password'),
                                    db_name=os.getenv('db_name')) as conn:
        if not Insurance.insurance_for_change:
            try:
                async with conn.cursor() as cur:
                    await cur.execute(
                        'INSERT INTO insurance (vehicle, license_plate, full_name, from_date, to_date, phone_number) '
                        'VALUES (%s, %s, %s, %s, %s, %s);',
                        (info_vehicle, license_plate, full_name, from_date, to_date, phone_number))
                    await conn.commit()
                    await message.answer('✅ Нову страховку успішно додано!', reply_markup=ADMIN_REPLY_KB)
            except Exception as e:
                print(f'Exception: {e}')
            finally:
                conn.close()
        else:
            try:
                async with conn.cursor() as cur:
                    await cur.execute('UPDATE insurance SET vehicle = %s, license_plate = %s, full_name = %s, '
                                      'from_date = %s, to_date = %s, phone_number = %s WHERE id = %s;',
                                      (info_vehicle, license_plate, full_name, from_date, to_date, phone_number,
                                       insurance_id))
                    await conn.commit()
                    await message.answer(f'✅ Інформацію про страховку №{insurance_id} успішно оновлено!',
                                         reply_markup=ADMIN_REPLY_KB)
            except Exception as e:
                print(f'Exception: {e}')
            finally:
                conn.close()

    await state.clear()
    Insurance.insurance_for_change = None


@admin_router.message(StateFilter(Insurance.enter_phone_number))
async def enter_phone_number_problem(message: Message):
    await message.answer('<b>👇 Введіть номер телефону страхувальника: </b>\n'
                         '<i>Правильний формат 0000000000</i>')
    return


########################################################################################################################
############################################## ДОДАТИ/ВИДАЛИТИ ПЕРСОНАЛ ################################################
########################################################################################################################
# class AddDeleteStaff(StatesGroup):
#     delete_process_start = State()
#     delete_process_end = State()
#
#     enter_name = State()
#     enter_phone = State()
#
#
# @admin_router.message(F.text == 'Додати/Видалити персонал')
# async def add_delete_staff_start(message: Message, state: FSMContext):
#     await message.answer('👇 <b>Оберіть дію:</b> ', reply_markup=get_callback_button(
#         btns={'Додати': 'staff_add', 'Видалити': 'staff_delete'}
#     ))
#     await state.set_state(AddDeleteStaff.delete_process_start)
#
#
# @admin_router.callback_query(F.data.in_(['staff_add', 'staff_delete']),
#                              StateFilter(AddDeleteStaff.delete_process_start))
# async def main_process(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#
#     if callback.data == 'staff_delete':
#         async with await get_connection(host=os.getenv('host'),
#                                         port=int(os.getenv('port')),
#                                         user=os.getenv('user'),
#                                         password=os.getenv('password'),
#                                         db_name=os.getenv('db_name')) as conn:
#             async with conn.cursor() as cur:
#                 await cur.execute('SELECT id, name FROM staff;')
#                 result_staff = await cur.fetchall()
#                 if result_staff:
#                     staff_dict = {str(res[1]): str(res[0]) for res in result_staff}
#                     staff_message = '\n'.join([f'🔹 {str(res[0])}: {str(res[1])}' for res in result_staff])
#                     await callback.message.answer('👇 <b>Наша команда</b>: \n\n'
#                                                   f'{staff_message}\n\n'
#                                                   f'👇 <b>Оберіть, кого бажаєте видалити: </b>',
#                                                   reply_markup=get_callback_button(
#                                                       btns=staff_dict
#                                                   ))
#                     await state.set_state(AddDeleteStaff.delete_process_end)
#                 else:
#                     await callback.message.answer('❌ Персоналу немає, нікого видаляти', reply_markup=ADMIN_REPLY_KB)
#                     await state.clear()
#     if callback.data == 'staff_add':
#         await callback.message.answer('👇 <b>Введіть ім’я працівника</b>: ', reply_markup=types.ReplyKeyboardRemove())
#         await state.set_state(AddDeleteStaff.enter_name)
#
#
# @admin_router.callback_query(F.data, StateFilter(AddDeleteStaff.delete_process_end))
# async def final_deleting(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#     staff_id = int(callback.data)
#     async with await get_connection(host=os.getenv('host'),
#                                     port=int(os.getenv('port')),
#                                     user=os.getenv('user'),
#                                     password=os.getenv('password'),
#                                     db_name=os.getenv('db_name')) as conn:
#         async with conn.cursor() as cur:
#             await cur.execute('DELETE FROM staff WHERE id = %s;', (staff_id,))
#             await conn.commit()
#
#     await callback.message.answer('<b>✅ Інформацію про працівника успішно видалено</b>', reply_markup=ADMIN_REPLY_KB)
#     await state.clear()
#
#
# @admin_router.message(F.text, StateFilter(AddDeleteStaff.enter_name))
# async def enter_name(message: Message, state: FSMContext):
#     if len(message.text) > 100:
#         await message.answer('👇 <b>Введіть ім’я заново</b>:\n\n'
#                              '<i>Завелике ім’я (не більше 100 символів)</i>')
#         return
#
#     await state.update_data(enter_name=message.text)
#     await message.answer('👇 <b>Введіть номер телефону працівника</b>:\n\n'
#                          '<i>Формат: 0000000000</i>')
#     await state.set_state(AddDeleteStaff.enter_phone)
#
#
# @admin_router.message(F.text, StateFilter(AddDeleteStaff.enter_phone))
# async def enter_phone(message: Message, state: FSMContext):
#     pattern = r"^0\d{9}$"
#     if re.fullmatch(pattern, message.text):
#         data = await state.get_data()
#         staff_name = data['enter_name']
#         phone_number = message.text
#         async with await get_connection(host=os.getenv('host'),
#                                         port=int(os.getenv('port')),
#                                         user=os.getenv('user'),
#                                         password=os.getenv('password'),
#                                         db_name=os.getenv('db_name')) as conn:
#             async with conn.cursor() as cur:
#                 await cur.execute('INSERT INTO staff (name, phone_number) '
#                                   'VALUES (%s, %s);', (staff_name, phone_number))
#                 await conn.commit()
#         await message.answer('<b>✅ Інформацію про працівника успішно додано</b>',
#                              reply_markup=ADMIN_REPLY_KB)
#         await state.clear()
#     else:
#         await message.answer('👇 <b>Введіть номер телефону заново</b>:\n\n'
#                              '<i>Правильний формат: 0000000000</i>')
#         return
#
#
# @admin_router.message(StateFilter(*[AddDeleteStaff.delete_process_start, AddDeleteStaff.delete_process_end,
#                                     AddDeleteStaff.enter_phone, AddDeleteStaff.enter_name]))
# async def message_problem(message: Message, state: FSMContext):
#     await message.answer('❌ Недопустимі дані!', reply_markup=ADMIN_REPLY_KB)
#     await state.clear()
