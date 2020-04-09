# Getting Started

1. Probably get yourself in a `virtualenv`, [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) is cool. 

1. `pip install -r requirements.txt`
    (You can get away with not installing `psycopg2` or `django-heroku`, both of which are dependencies for Heroku deployment, could refactor these into a different file)

1. `./manage.py migrate`

1. Get redis running, install if needed.

1. `./manage.py runserver`

1. Go to `localhost:8000` in your browser.

## First time only

Make yourself a superuser with `./manage.py createsuperuser` then you can go to `localhost:8000/admin` and see all the cool Django admin stuff.
