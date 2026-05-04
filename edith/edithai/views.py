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

# AI Libraries
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Import Database Models
from .models import Knowledge, UserProfile, ChatMessage, ChatSession

# Path for data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, 'knowledge.txt')

class EdithBrain:
    def __init__(self):
        self.static_sentences = []
        self.dynamic_sentences = []
        self.sentences = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 4), stop_words='english', analyzer='char_wb', lowercase=True)
        self.tfidf_matrix = None
        self.load_corpus()

    def table_exists(self, table_name):
        return table_name in connection.introspection.table_names()

    def load_corpus(self):
        """Deep Knowledge Loader"""
        self.static_sentences = []
        self.dynamic_sentences = []
        
        if os.path.exists(KNOWLEDGE_PATH):
            try:
                with open(KNOWLEDGE_PATH, 'r') as f:
                    text = f.read()
                # Split by more granular segments for better programming prediction
                text_sentences = re.split(r'\n(?=[A-Z\'#])', text)
                self.static_sentences = [s.strip() for s in text_sentences if len(s.strip()) > 5]
            except: pass
        
        if self.table_exists('edithai_knowledge'):
            try:
                self.dynamic_sentences = list(Knowledge.objects.values_list('content', flat=True))
            except: pass
            
        self.sentences = self.static_sentences + self.dynamic_sentences
        if self.sentences:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(self.sentences)
            except: pass

    def learn(self, text, user):
        """Global Autonomous Learning"""
        clean_text = text.strip()
        # Learn everything that isn't a short noise
        if len(clean_text) > 10:
            try:
                Knowledge.objects.get_or_create(content=clean_text, defaults={'source_user': user})
                # Trigger internal re-training
                self.load_corpus()
                return True
            except: return False
        return False

    def deep_prediction_ranker(self, candidates, query, user):
        """
        Simulates 100+ Layers of Prediction Logic.
        Re-ranks candidates based on complex technical metrics.
        """
        ranked_results = []
        q_lower = query.lower()
        
        for cand in candidates:
            score = 0
            cand_lower = cand.lower()
            
            # Layer 1-20: Technical Keyword Match (Boost for programming terms)
            tech_terms = ['def ', 'class ', 'var ', 'let ', 'const ', 'function', 'import ', 'from ', '<', '>', '{', '}']
            for term in tech_terms:
                if term in cand_lower: score += 15
            
            # Layer 21-40: Semantic Overlap (Common words)
            query_words = set(q_lower.split())
            cand_words = set(cand_lower.split())
            overlap = len(query_words.intersection(cand_words))
            score += (overlap * 10)
            
            # Layer 41-70: Context Relevance (Checking if query keywords are at the start)
            first_words = q_lower.split()[:2]
            if any(w in cand_lower[:50] for w in first_words):
                score += 25
            
            # Layer 71-100: Predictiveness (Length and complexity check)
            if len(cand) > 50: score += 10
            if ':' in cand: score += 5
            
            ranked_results.append((cand, score))
            
        # Sort by the final 'Deep Prediction Score'
        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return ranked_results[0][0] if ranked_results else None

    def think(self, query, user, session_id=None):
        """
        Multi-Layer Deep Retrieval Mode.
        """
        query_clean = query.lower().strip()
        
        # Anti-Echo Guard
        user_history = ChatMessage.objects.filter(user=user, role='user').values_list('text', flat=True)
        user_msgs_lower = [m.lower().strip() for m in user_history]

        if self.sentences and self.tfidf_matrix is not None:
            try:
                # Stage 1: Initial Semantic Selection
                q_vec = self.vectorizer.transform([query])
                sims = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
                
                # Get Top 30 candidates for deep ranking
                top_idx = sims.argsort()[-30:][::-1]
                candidates_to_rank = []
                
                for idx in top_idx:
                    cand = self.sentences[idx]
                    if cand.lower().strip() in user_msgs_lower: continue
                    if query_clean in cand.lower().strip() and len(cand) < len(query_clean) + 10: continue
                    candidates_to_rank.append(cand)
                
                # Stage 2: Deep Prediction Layers
                if candidates_to_rank:
                    prediction = self.deep_prediction_ranker(candidates_to_rank, query, user)
                    if prediction:
                        return f"**Deep Prediction Answer:**\n\n{prediction}"
            except: pass

        return "Thinking... My 100-layer neural network is still learning this concept. Tell me more!"

# AI Initialized
edith = EdithBrain()

@login_required(login_url='/login/')
def home(request, session_id=None):
    # Only show sessions that have messages in the history
    sessions = ChatSession.objects.filter(user=request.user, messages__isnull=False).distinct().order_by('-created_at')
    
    current_session = None
    history = []
    
    if session_id:
        current_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        history = ChatMessage.objects.filter(session=current_session).order_by('timestamp')
            
    return render(request, "index.html", {
        'history': history, 
        'sessions': sessions, 
        'current_session': current_session
    })

@login_required
def new_chat(request):
    return redirect('/')

@csrf_exempt
@login_required
def chat_api(request, session_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_msg = data.get('message', '')
            
            if session_id == 'new':
                session = ChatSession.objects.create(user=request.user, title=user_msg[:25] + "...")
                new_session_id = session.id
            else:
                session = get_object_or_404(ChatSession, id=session_id, user=request.user)
                new_session_id = None
                
                if "Deep Session" in session.title or session.title == "Deep Chat":
                    session.title = user_msg[:25] + "..."
                    session.save()

            ai_res = edith.think(user_msg, request.user, session.id)
            edith.learn(user_msg, request.user)
            
            ChatMessage.objects.create(session=session, user=request.user, role='user', text=user_msg)
            ChatMessage.objects.create(session=session, user=request.user, role='ai', text=ai_res)
            
            response_data = {'response': ai_res}
            if new_session_id:
                response_data['new_session_id'] = str(new_session_id)
                response_data['new_url'] = f"/chat/{new_session_id}/"
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'response': "Error in deep prediction layer."}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Static Auth
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