from django.shortcuts import render

def inicio(request):
    return render(request, 'core/inicio.html')

def que_es(request):
    return render(request, 'core/que_es.html')

