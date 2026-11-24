from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def iniciar_tramite(request):
    """Vista para iniciar el trámite de licencia"""
    return render(request, 'licencias/iniciar.html')