# Planetarium-API

API service for cinema management written on DRF

## Features

* JWT authenticated
* Admin panel /admin/
* Documentation is located at /api/doc/swagger/
* Managing Reservations and tickets
* Creating astronomy shows with show themes
* Creating planetarium domes
* Adding show sessions
* Filtering and searching

## Installing using GitHub

Python3 must be already installed

## Environment variables

Create a `.env` file following the `.env.sample` template and replace with your values.

```shell
git clone https://github.com/VladyslavBon/Planetarium-API
cd planetarium_api

python3 -m venv venv
- For Linux or Mac:
    source venv/bin/activate
- For Windows:
    source venv/Scripts/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Run with Docker

Docker should be installed

```shell
docker-compose build
docker-compose up
```

## Getting Access

* create user via api/user/register/
* get access token via api/user/token/