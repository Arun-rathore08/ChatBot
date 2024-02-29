from datetime import timezone
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from openai import *
from .models import Chat
from django_ChatGPT import settings
from django.core.mail import send_mail, EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str 
from .tokens import generate_token
from django.contrib.auth.decorators import login_required
# Create your views here.



def index(request):
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['fname']
        last_name = request.POST['lname']
        email = request.POST['email']
        pass1 = request.POST['pass1']
        pass2 = request.POST['pass2']

        if User.objects.filter(username=username):
            messages.error(request, "Username Already Exist, Please Try Another Username")
            return redirect('register')
        if User.objects.filter(email=email):
            messages.error(request, "This email is already registered")
            return redirect('register')
        if pass1 != pass2:
            messages.error(request, "Password didn't match!")
            return redirect('register')
        if not username.isalnum():
            messages.error(request, "Username must contain alphabets and numbers only!")
            return redirect('register')
        


        myuser = User.objects.create_user(username, email, pass1)
        myuser.first_name = first_name
        myuser.last_name = last_name
        myuser.is_active= True
        myuser.save()
        return redirect('login')

        current_site = get_current_site(request)
        email_subject = "Confirmation mail @ myAI"
        email_message = render_to_string("email_confirmation.html", {
            'name' : myuser.first_name,
            'domain' : current_site.domain,
            'uid' : urlsafe_base64_encode(force_bytes(myuser.pk)),
            'token' : generate_token.make_token(myuser)
        })

        email = EmailMessage(
            email_subject,
            email_message, 
            settings.EMAIL_HOST_USER, 
            [myuser.email],
        )

        email.fail_silently = True
        email.send()

    return render(request, 'register.html')


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        myuser = None
    
        if myuser is not None and generate_token.check_token(myuser, token):
            myuser.is_active = True
            login(request, myuser)
            return redirect('chat')
        else:
            return render(request, 'activation_failed.html')
        

def login(request):
    if request.method == 'POST':
        username= request.POST['username']
        pass1 = request.POST['pass1']
        user = authenticate(username = username, password = pass1)

        if user is not None:
            auth_login(request, user)
            return redirect('chat')
        else:
            messages.error(request, "Bad Credential!")
            return redirect('login')
    else:
        return render(request, 'login.html')

client = OpenAI(api_key='Enter Your API Key')

# openai_api_key = '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'
# openai.api_key = openai_api_key


def ask_openai(message):
    try:
        # response = "hi this is my response"
        response = client.Chat.Completions.create(
            engine = "text-devinci-003",
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message},
            ],
            tokens = 256,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        # Handle API request errors
        answer = f"Error: {e}"

    return answer

@login_required
def chat(request):
    chats = Chat.objects.filter(user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message') 
        response = ask_openai(message)

        chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now())
        chat.save()

        return JsonResponse({'message': message, 'response': response})
    
    return render(request, 'chat.html', {'chats': chats})

'''
def chat(request):
    chats = Chat.objects.filter(user=request.user)
    if request.method == "POST":
        message = request.POST.get('message')
        response = openai.ChatCompletion.create(
            model = 'gpt-3.5-turbo',
            
        )
'''


# def ask_openai(message):
#     response = openai.chatCompletion.create(
#         model = "gpt-4",
#         messages=[
#             {"role": "system", "content": "You are an helpful assistant."},
#             {"role": "user", "content": message},
#         ]
#     )
    
#     answer = response.choices[0].message.content.strip()
#     return answer



# # Create your views here.
# @login_required
# def chat(request):
#     chats = Chat.objects.filter(user=request.user)

#     if request.method == 'POST':
#         message = request.POST.get('message')
#         response = ask_openai(message)

#         chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now())
#         chat.save()
#         return JsonResponse({'message': message, 'response': response})
#     return render(request, 'chat.html', {'chats': chats})

@login_required
def logout(request):
    auth_logout(request)
    return redirect('login')
