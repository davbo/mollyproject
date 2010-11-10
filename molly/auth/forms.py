from django import forms

from django.forms.models import BaseModelFormSet, modelformset_factory

from .models import ExternalServiceToken, UserSession

class TrueEmptyTuple(tuple):
    def __init__(self):
        super(TrueEmptyTuple, self).__init__(())
    def __nonzero__(self):
        return True

class PreferencesForm(forms.Form):
    old_pin = forms.RegexField(r'[0-9a-zA-Z]{4,}',
        label='Old PIN',
        required=False,
        widget=forms.PasswordInput())
    new_pin_a = forms.RegexField(r'[0-9a-zA-Z]{4,}',
        label='New PIN',
        required=False,
        widget=forms.PasswordInput())
    new_pin_b = forms.RegexField(r'[0-9a-zA-Z]{4,}',
        label='Repeat PIN',
        required=False,
        widget=forms.PasswordInput())

    timeout_period = forms.IntegerField(
        min_value=5,
        max_value=720)

def UserSessionFormSet(request, *args, **kwargs):
    formset = modelformset_factory(UserSession, fields=TrueEmptyTuple(), extra=0, can_delete=True)
    return formset(
        queryset=UserSession.objects.filter(user=request.user).order_by('-last_used'),
        prefix="user-sessions",
        *args, **kwargs
    )

def ExternalServiceTokenFormSet(request, *args, **kwargs):
    formset = modelformset_factory(ExternalServiceToken, fields=TrueEmptyTuple(), extra=0, can_delete=True)
    return formset(
        queryset=ExternalServiceToken.objects.filter(user=request.user, authorized=True),
        prefix="external-service-tokens",
        *args, **kwargs
    )