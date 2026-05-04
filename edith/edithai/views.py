import os
import json
import random
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import connection

# AI Libraries for Semantic Understanding
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Import our custom database tables
from .models import Knowledge, UserProfile, ChatMessage, ChatSession

# Base knowledge file path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, 'knowledge.txt')

class EdithBrain:
    def __init__(self):
        # sentences: Saari knowledge (file + database) yahan store hogi
        self.sentences = []
        # vectorizer: Text ko numbers (vectors) me convert karne wala tool
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english', lowercase=True)
        self.tfidf_matrix = None
        self.load_corpus()

    def table_exists(self, table_name):
        """Database table check karne ka logic taaki migrations ke waqt crash na ho"""
        return table_name in connection.introspection.table_names()

    def load_corpus(self):
        """Loads static file and dynamic DB knowledge separately"""
        self.static_sentences = []
        self.dynamic_sentences = []
        
        # 1. Static Knowledge (knowledge.txt)
        if os.path.exists(KNOWLEDGE_PATH):
            try:
                with open(KNOWLEDGE_PATH, 'r') as f:
                    text = f.read()
                text_sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s+', text)
                self.static_sentences = [s.strip() for s in text_sentences if len(s.strip()) > 5]
            except: pass
        
        # 2. Dynamic Knowledge (Database)
        if self.table_exists('edithai_knowledge'):
            try:
                self.dynamic_sentences = list(Knowledge.objects.values_list('content', flat=True))
            except: pass
            
        # Combine all for vectorizer
        self.sentences = self.static_sentences + self.dynamic_sentences
        if self.sentences:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(self.sentences)
            except: pass

    def learn(self, text, user):
        """Only learn declarative facts, NO questions"""
        clean_text = text.strip()
        if '?' in clean_text or any(w in clean_text.lower() for w in ['what', 'how', 'why', 'can you']):
            return False

        if len(clean_text) > 10:
            try:
                Knowledge.objects.get_or_create(content=clean_text, defaults={'source_user': user})
                self.load_corpus()
                return True
            except: return False
        return False

    def think(self, query, user, session_id=None):
        """Double-Brain Retrieval Logic"""
        query_clean = query.lower().replace('?', '').strip()
        
        # Anti-Echo: Get list of user's own messages to never repeat them
        user_msgs = ChatMessage.objects.filter(user=user, role='user').values_list('text', flat=True)
        user_msgs_lower = [m.lower().strip() for m in user_msgs]

        # 1. TECH BOOSTER
        tech_keywords = ['html', 'css', 'js', 'javascript', 'python', 'django', 'tag', 'element', 'web', 'browser']
        is_tech = any(k in query_clean for k in tech_keywords)

        if self.sentences and self.tfidf_matrix is not None:
            try:
                q_vec = self.vectorizer.transform([query])
                sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
                top_idx = sims.argsort()[-15:][::-1]

                best_static = None
                best_dynamic = None

                for idx in top_idx:
                    candidate = self.sentences[idx]
                    score = sims[idx]
                    cand_lower = candidate.lower().strip()

                    # STRICT FILTERS
                    if cand_lower in user_msgs_lower: continue 
                    if cand_lower == query_clean: continue 
                    if '?' in candidate: continue 

                    # Check if it's from static or dynamic pool
                    if candidate in self.static_sentences:
                        if not best_static or score > 0.3:
                            best_static = candidate
                    else:
                        if not best_dynamic or score > 0.4:
                            best_dynamic = candidate

                # Priority: Tech Query -> Static Brain | General -> Dynamic Brain
                if is_tech and best_static: return best_static
                if best_dynamic: return best_dynamic
                if best_static: return best_static
            except: pass

        return "I am absorbing this knowledge. Tell me more technical details about HTML or CSS!"

        return "I'm listening and learning! Ask me more technical questions about HTML/CSS/JS."

# Edith ka ek instance banao jo server chalne par active rahega
edith = EdithBrain()

@login_required(login_url='/login/')
def home(request, session_id=None):
    """Chat Page ko render karne ka function"""
    # User ki saari purani chat sessions dhoondho
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
    
    if session_id:
        # Agar URL me ID hai, to wahi chat kholo
        current_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    else:
        # Agar ID nahi hai, to sabse latest wali kholo ya nayi banao
        current_session = sessions.first()
        if not current_session:
            current_session = ChatSession.objects.create(user=request.user, title="First Conversation")
            return redirect('home_with_session', session_id=current_session.id)
            
    # Session ki message history load karo
    history = ChatMessage.objects.filter(session=current_session).order_by('timestamp')
    
    return render(request, "index.html", {
        'history': history, 
        'sessions': sessions, 
        'current_session': current_session
    })

@login_required
def new_chat(request):
    """Nayi Chat start karne ka logic"""
    session = ChatSession.objects.create(user=request.user, title="New Chat Session")
    return redirect('home_with_session', session_id=session.id)

@csrf_exempt
@login_required
def chat_api(request, session_id):
    """
    Real-time Chat API: Jab user message bhejta hai, ye function trigger hota hai.
    """
    if request.method == 'POST':
        try:
            # 1. Session dhoondho
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
            data = json.loads(request.body)
            user_msg = data.get('message', '')
            
            # 2. AI RESPONSE: Sawal ka jawab dhoondhna
            ai_res = edith.think(user_msg, request.user, session_id)
            
            # 3. AUTONOMOUS LEARNING: Har baar user ka message seekhna
            edith.learn(user_msg, request.user)
            
            # 4. HISTORY STORAGE: Dono messages ko database me save karna
            ChatMessage.objects.create(session=session, user=request.user, role='user', text=user_msg)
            ChatMessage.objects.create(session=session, user=request.user, role='ai', text=ai_res)
            
            # 5. AUTO TITLE: Pehle message ke basis par chat ka naam badalna
            if session.title == "New Chat Session" or session.title == "First Conversation":
                session.title = user_msg[:25] + "..."
                session.save()
            
            return JsonResponse({'response': ai_res})
        except Exception as e:
            # Error hone par response dikhana
            return JsonResponse({'response': f"Thinking Error: {str(e)}"}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Authentication Views (Login/Signup/Logout)
def signup_view(request):
    if request.method == 'POST':
        data = request.POST
        if User.objects.filter(username=data['username']).exists():
            return render(request, 'signup.html', {'error': 'Username already exists'})
        user = User.objects.create_user(username=data['username'], email=data['email'], password=data['password'])
        login(request, user)
        return redirect('/')
    return render(request, 'signup.html')

def login_view(request):
    if request.method == 'POST':
        data = request.POST
        user = authenticate(request, username=data['username'], password=data['password'])
        if user is not None:
            login(request, user)
            return redirect('/')
        return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('/login/')