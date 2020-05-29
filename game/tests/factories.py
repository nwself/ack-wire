from django.contrib.auth import get_user_model
import factory
import factory.fuzzy

from ..models import Game


class UserFactory(factory.django.DjangoModelFactory):

    username = factory.Faker("user_name")

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]


class GameFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()

    class Meta:
        model = Game

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for user in extracted:
                self.users.add(user)
