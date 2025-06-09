[https://github.com/pxe-la/Async_API](https://github.com/pxe-la/Async_API)

## Локальная разработка
1.  Cоздайте файл `.env` на основе `.env.example`
2.  Установите зависимости
    ```bash
    pip install poetry
    poetry install
    ```
3. Устаноите пре-коммит хуки:
    ```bash
    pre-commit install
    ```
4. Запустите окружение:
    ```bash
    docker-compose up -d
    ```
4. Для запуска определенного сервиса см. README в папке сервиса

## Продовый запуск
1.  Cоздайте файл `.env` на основе `.env.example`
2.  Запустите проект:
    ```bash
    docker-compose -f docker-compose.yml up -d
    ```
