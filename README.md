Ознакомиться с проектом вы можете по следующей ссылке: https://thebestfoodgram.zapto.org/

# Описание:
Данный проект - это удобная и приятная площадка, на которой вы можете выкладывать рецепты, а также смотреть уже добавленые рецепты. Вы можете зарегистрироваться, смотреть, выкладывать рецепты, добавлять к ним ингредиенты, теги, время приготовления, описание приготовление, а также добавлять к рецептам фотки. Также можно редактировать и удалять рецепты. Понравившиеся рецепты можно добавить в список покупок. Есть возможность подписаться на авторов рецептов и следить за ними. И под конец, очень удобная фунция, с помощью которой можно скачать список покупок с нужными к ним ингредиентами. Проект разбит на 3 контейнера: backend, frontend, gateway(nginx).

Технологический стек: 
- Django
- DRF (Django Rest Framework)
- Pillow
- Docker
- Nginx

# Как развернуть проект:
В .env файла должна быть следующая информация:
```
SECRET_KEY=example
DEBUG=True/False # (в зависимости от ваших нужд)
ALLOWED_HOSTS=example
DB_ENGINE=sqlite/postgres # (в зависимости от ваших нужд)
POSTGRES_USER=example
POSTGRES_PASSWORD=example
POSTGRES_DB=example
DB_HOST=example
DB_PORT=example
```

Скачайте docker-compose.production.yml, в директории этого файла пропишите команду (ЕСЛИ РАБОТАЕТ НА LINUX КАЖДУЮ КОМАНДУ ДЕЛАЙТЕ С "sudo"):
```bash
docker compose -f docker-compose.production.yml up
```

```bash
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
```

```bash
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
```

```bash
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

# Реквизиты
Автор: Элиханов Рамзан

GitHub: https://github.com/Griver2006
