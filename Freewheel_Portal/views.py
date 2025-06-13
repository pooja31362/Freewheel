from django.shortcuts import render
def home(request):
    return render(request, 'Freewheel_Portal/home.html', {'range': range(15) })
# Create your views here.
