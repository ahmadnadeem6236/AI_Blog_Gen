from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect,render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
from os import getenv
from dotenv import load_dotenv
import google.generativeai as genai
from .models import BlogPost


load_dotenv()

# Create your views here.

@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except(KeyError,json.JSONDecodeError):
            return JsonResponse({'error':'Invalid Data send'}, status=400)

        # get yt title
        title = yt_title(yt_link)
        

        #get transcript
        transcription = get_transcript(yt_link)
        if not transcription:
            return JsonResponse({'error': 'Failed to get transcription'}, status=500)

        #use Google gemnini to gen blog
        blog_content = get_blog(transcription)
        if not blog_content:
            return JsonResponse({'error': 'Failed to get blog'}, status=500)


        # save blog article to db
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
            )

        new_blog_article.save()




        # return blog article as response
        return JsonResponse({'content':blog_content})
        
    else:
        return JsonResponse({'error': 'Invalid'}, status=405)



def get_blog(transcription):
    genai.configure(api_key=getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"
    response = model.generate_content(prompt)

    return response.text



def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcript(link):
    audio_file = download_audio(link)
    
    aai.settings.api_key = getenv('ASSEMBLY_AI_API')

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text


def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})


def blog_details(request,pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        redirect('/')

    


    
    return render(request, 'blog-details.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid Username or Password'
            return render(request, 'login.html', {'error':error_message})


    
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html',{'error_message':error_message})

                
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html',{'error_message':error_message})


        
    return render(request, 'signup.html')


def user_logout(request):
    logout(request)
    
    

    return redirect('/')