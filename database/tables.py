import asyncio
import os

from database.connection import get_connection, create_database
from dotenv import load_dotenv

load_dotenv()


########################################################################################################################
async def create_db():
    await create_database(host=str(os.getenv('host')),
                          port=int(os.getenv('port')),
                          user=str(os.getenv('user')),
                          password=str(os.getenv('password')),
                          db_name=str(os.getenv('db_name')))


########################################################################################################################
async def users_A(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS users_A ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'name VARCHAR(500), '
                          'unique_code INT UNSIGNED);')
        await conn.commit()


async def users_B(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS users_B ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'name VARCHAR(500), '
                          'unique_code INT UNSIGNED);')
        await conn.commit()


async def users_C(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS users_C ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'name VARCHAR(500), '
                          'unique_code INT UNSIGNED);')
        await conn.commit()


async def pumps(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS pumps ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'photo TEXT, '
                          'sku VARCHAR(25), '
                          'name VARCHAR(250), '
                          'brand VARCHAR(75), '
                          'basic_price DECIMAL(7,3), '
                          'in_one_pack VARCHAR(10), '
                          'link TEXT, '
                          'discount VARCHAR(25));')
        await conn.commit()


async def plumbing(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS plumbing ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'photo TEXT, '
                          'sku VARCHAR(25), '
                          'name VARCHAR(250), '
                          'brand VARCHAR(75), '
                          'basic_price DECIMAL(7,3), '
                          'in_one_pack VARCHAR(10), '
                          'link TEXT, '
                          'discount VARCHAR(25));')
        await conn.commit()


async def garden_inventory(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS garden_inventory ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'photo TEXT, '
                          'sku VARCHAR(25), '
                          'name VARCHAR(250), '
                          'brand VARCHAR(75), '
                          'basic_price DECIMAL(7,3), '
                          'in_one_pack VARCHAR(10), '
                          'special_category VARCHAR(100), '
                          'link TEXT, '
                          'discount VARCHAR(25));')
        await conn.commit()


async def actual_course(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS actual_course ('
                          'id SMALLINT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'actual_course DECIMAL(6,3));')
        await conn.commit()


async def insurance(conn):
    async with conn.cursor() as cur:
        await cur.execute('CREATE TABLE IF NOT EXISTS insurance ('
                          'id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT, '
                          'vehicle VARCHAR(250), '
                          'license_plate VARCHAR(25), '
                          'full_name VARCHAR(100), '
                          'from_date DATE, '
                          'to_date DATE, '
                          'phone_number VARCHAR(10)'
                          ');')
        await conn.commit()


async def main():
    await create_db()
    conn = await get_connection(host=str(os.getenv('host')),
                                port=int(os.getenv('port')),
                                user=str(os.getenv('user')),
                                password=str(os.getenv('password')),
                                db_name=str(os.getenv('db_name')))
    await users_A(conn)
    await users_B(conn)
    await users_C(conn)
    await pumps(conn)
    await plumbing(conn)
    await garden_inventory(conn)
    await actual_course(conn)
    await insurance(conn)


if __name__ == '__main__':
    asyncio.run(main())
