from django.urls import path
from . import views

# URLCONF
urlpatterns = [
    path('hello/', views.say_hello),
    path('hello_html/', views.say_hello_html)
]