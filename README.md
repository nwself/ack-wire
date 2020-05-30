# Getting Started

1. Probably get yourself in a `virtualenv`, [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) is cool. 

1. `pip install -r requirements.txt`
    (You can get away with not installing `psycopg2` or `django-heroku`, both of which are dependencies for Heroku deployment, could refactor these into a different file)

1. `./manage.py migrate`

1. Get redis running, install if needed.

1. (optional?) Get Django Channels running: `daphne acquire.asgi:application --port 8000 --bind 0.0.0.0 -v2`

1. `./manage.py runserver`

1. Go to `localhost:8000` in your browser.

## First time only

Make yourself a superuser with `./manage.py createsuperuser` then you can go to `localhost:8000/admin` and see all the cool Django admin stuff.

# TODOs
- Major update of create game page
    - Enforce that user creating game is in game
    - Select2 or something reasonable for finding users to add to game
    - Add optional config (stock names, price schedule, board size)
- Sort lobby into active and completed games
- Fix declare chain buttons for mobile
  - Possibly change all buttons to some reasonable style & size, esp. stock buying +/-
- Warn if buying less than 3 stocks and player still has money

### Start game in shell

Create a game in the shell with:
```python
from game.views import start_game
from game.models import Game
g = Game.objects.create(name='game-name')
g.users.add(u1)
g.users.add(u2)
g.save()
start_game(game, other_options)
```
