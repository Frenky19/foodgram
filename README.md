# [Foodgram - Продуктовый помощник.](https://foodgram-frenky19.zapto.org/)
Foodgram - это онлайн-сервис для любителей кулинарии, где пользователи могут публиковать рецепты, подписываться на других авторов, добавлять понравившиеся рецепты в избранное и формировать список покупок для выбранных блюд.

[![Foodgram Workflow](https://github.com/Frenky19/foodgram/actions/workflows/main.yml/badge.svg?event=push)](https://github.com/Frenky19/foodgram/actions/workflows/main.yml)

## Основные возможности
- Создание, редактирование и удаление рецептов

- Добавление рецептов в избранное

- Формирование списка покупок

- Скачивание списка покупок в виде текстового файла

- Подписка на других пользователей

- Поиск рецептов по ингредиентам и тегам

- Аутентификация по токену

- Управление профилем пользователя (включая аватар)

## Стек технологий

![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions&logoColor=white)

## Требования

- Python 3.9 (можно использовать версии выше, но стоит убедиться, что не будет конфликта зависимостей)
- Node.js 18+
- Docker
- Аккаунт на Docker Hub
- SSH-доступ к серверу
- Telegram-бот (для уведомлений)

## Настройка секретов

Добавьте в Secrets репозитория:

```
DOCKER_USERNAME - Логин Docker Hub
DOCKER_PASSWORD - Пароль Docker Hub
HOST - IP сервера
USER - Логин пользователя сервера
SSH_KEY - Приватный ключ SSH
SSH_PASSPHRASE - Код для ключа
TELEGRAM_TO - ID чата Telegram
TELEGRAM_TOKEN - Токен бота Telegram
GATEWAY_IMAGE - Образ сервиса gateway на Dockerhub
FRONTEND_IMAGE - Образ frontend сервиса на Dockerhub
BACKEND_IMAGE - Образ backend сервиса на Dockerhub
```

Скопируйте файл .env на сервер (или создайте вручную), в директорию проекта:

```
scp -i path_to_SSH/SSH_name .env \
    username@server_ip:/home/username/<директория проекта>/.env 
```

На сервере в редакторе nano откройте конфиг Nginx: sudo nano /etc/nginx/sites-enabled/default. Измените все настройки location на одну в секции server.

```
location / {
        proxy_set_header Host $http_host;
        proxy_pass http://127.0.0.1:8000;
    }
```

Перезагрузите конфиг Nginx:

```
sudo service nginx reload 
```

## Деплой

После пуша в ветку main:

- Автоматически запускаются тесты

- Собираются и публикуются Docker-образы

- Разворачивается на сервере через docker-compose

- При успехе - отправляется уведомление в Telegram

## Инструкция по локальному запуску

Клонируйте репозиторий:

```
git clone https://github.com/Frenky19/foodgram.git
```

Создайте файл .env в корневой директории со следующим содержимым:

```
SECRET_KEY=ваш-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,foodgram-frenky19.zapto.org
SQLITE=False
DB_HOST=db
DB_PORT=5432
POSTGRES_USER=django_user
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=django
CSRF_TRUSTED_ORIGINS=https://foodgram-frenky19.zapto.org,http://127.0.0.1:8080,http://localhost:8080
```

Запустите контейнеры:

```
docker-compose up -d --build
```

Создайте миграции:

```
docker-compose exec backend python manage.py makemigrations
```

Выполните миграции:

```
docker-compose exec backend python manage.py migrate
```

Соберите статические файлы:

```
docker-compose exec backend python manage.py collectstatic --no-input
```

Создайте суперпользователя (опционально):

```
docker-compose exec backend python manage.py createsuperuser
```

Заполните базу данных начальными данными (ингредиенты и теги).(надо сделать скрипт)

Проект будет доступен по адресу: http://localhost/

## Структура проекта

```
.
├── backend/    # Backend приложение Django
├── frontend/   # Frontend приложение React
├── nginx/      # Конфигурация шлюза nginx
└── docker-compose.production.yml
```

## API Endpoints

Документация:

- GET /schema/ - Скачивание API документации локально в формате .yml

- GET /schema/redoc/ - Просмотр API документации на основе сгенерированной схемы в интерфейсе Redoc

Пользователи:

- POST /api/users/ - Регистрация нового пользователя

- POST /api/auth/token/login/ - Получение токена аутентификации

- POST /api/auth/token/logout/ - Удаление токена аутентификации

- GET /api/users/ - Список пользователей

- GET /api/users/me/ - Профиль текущего пользователя

- GET /api/users/{id}/ - Профиль пользователя по ID

- GET /api/users/subscriptions/ - Мои подписки

- POST /api/users/{id}/subscribe/ - Подписаться на пользователя

- DELETE /api/users/{id}/subscribe/ - Отписаться от пользователя

- PUT /api/users/me/avatar/ - Обновить аватар

- DELETE /api/users/me/avatar/ - Удалить аватар

Теги:

- GET /api/tags/ - Список тегов

- GET /api/tags/{id}/ - Получить тег по ID

Ингредиенты:

- GET /api/ingredients/ - Список ингредиентов (с поиском)

- GET /api/ingredients/{id}/ - Получить ингредиент по ID

Рецепты:

- GET /api/recipes/ - Список рецептов (с фильтрацией)

- POST /api/recipes/ - Создать рецепт

- GET /api/recipes/{id}/ - Получить рецепт по ID

- PATCH /api/recipes/{id}/ - Обновить рецепт

- DELETE /api/recipes/{id}/ - Удалить рецепт

- GET /api/recipes/{id}/get-link/ - Получить короткую ссылку на рецепт

- POST /api/recipes/{id}/favorite/ - Добавить рецепт в избранное

- DELETE /api/recipes/{id}/favorite/ - Удалить рецепт из избранного

- POST /api/recipes/{id}/shopping_cart/ - Добавить рецепт в корзину

- DELETE /api/recipes/{id}/shopping_cart/ - Удалить рецепт из корзины

- GET /api/recipes/download_shopping_cart/ - Скачать список покупок

## Примеры запросов

Регистрация пользователя:

```
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
        "email": "user@example.com",
        "username": "newuser",
        "first_name": "John",
        "last_name": "Doe",
        "password": "securepassword123"
      }'
```

Получение токена:

```
curl -X POST http://localhost:8000/api/auth/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```

Создание рецепта:

```
curl -X POST http://localhost:8000/api/recipes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token ваш-токен" \
  -d '{
        "name": "Новый рецепт",
        "image": "data:image/png;base64,...",
        "text": "Описание рецепта",
        "cooking_time": 30,
        "tags": [1, 2],
        "ingredients": [
          {"id": 1, "amount": 200},
          {"id": 2, "amount": 50}
        ]
      }'
```

## Автор  
[Андрей Головушкин / Andrey Golovushkin](https://github.com/Frenky19)
