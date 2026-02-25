import aiomysql

#Создаем базу данных
async def create_database(*,
                          host: str,
                          port: int,
                          user: str,
                          password: str,
                          db_name: str):
    host = host
    port = port
    user = user
    password = password
    db = db_name
    conn = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password
    )
    async with conn.cursor() as cur:
        await cur.execute(f'CREATE DATABASE IF NOT EXISTS {db};')
        print(f'DB {db} was successfully created!')
    conn.close()

#Подключаемся к базе
async def get_connection(*,
                         host: str,
                         port: int,
                         user: str,
                         password: str,
                         db_name: str):
    try:
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db_name
        )
        print(f'Connection established to {db_name} with id {id(conn)}')
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None
