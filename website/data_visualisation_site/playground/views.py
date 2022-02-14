from django.shortcuts import render
from django.http import HttpResponse
from matplotlib import pyplot as plt
import pandas as pd
import os

# Create your views here.
# Request -> response
# Request handler
def say_hello(request):
    return HttpResponse('Hello world!')
def say_hello_html(request):
    x=1
    return render(request, 'hello.html', {'name' : 'Mosh'})
def plot_data():
    data_path = os.getcwd() + "//data//dataLog.csv"
    
