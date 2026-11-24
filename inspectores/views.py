from django.shortcuts import render

def lista(request):
    return render(request, 'inspectores/lista.html')