from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView


from .forms import CreateMatchaForm
from .models import MatchaGame


class MatchaCreate(LoginRequiredMixin, CreateView):
    # model = MatchaGame
    # fields = ['name', 'users']
    form_class = CreateMatchaForm
    template_name = "matcha/matcha_create.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        # This is not the right way to do this, super saves then we save again :/
        form.instance.users.add(self.request.user)
        form.instance.save()

        form.instance.start_game()

        return response


class MatchaDetail(DetailView):
    model = MatchaGame
    slug_field = 'name'
    slug_url_kwarg = 'name'
    template_name = "matcha/matcha_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game_state'] = self.object.get_active_state(for_=self.request.user)
        return context
