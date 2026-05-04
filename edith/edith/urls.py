from django.contrib import admin
from django.urls import path
from edithai.views import home, chat_api, login_view, signup_view, logout_view, new_chat

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('chat/<str:session_id>/', home, name='home_with_session'),
    path('new_chat/', new_chat, name='new_chat'),
    path('api/chat/<str:session_id>/', chat_api, name='chat_api'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
]
