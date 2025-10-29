# Django Project Structure for AutomatingLetter

## Overview
Converting the Flask project to Django with best practices and scalability.

---

## Recommended Project Structure

```
automating_letter/                          # Root directory
├── manage.py                               # Django management script
├── requirements.txt                        # Python dependencies
├── .env                                    # Environment variables
├── .gitignore                              # Git ignore rules
├── README.md                               # Project documentation
├── pytest.ini                              # Pytest configuration
├── docker-compose.yml                      # Docker setup (optional)
│
├── config/                                 # Project configuration
│   ├── __init__.py
│   ├── settings.py                         # Django settings (replaces src/config/settings.py)
│   ├── urls.py                             # Root URL configuration
│   ├── wsgi.py                             # WSGI entry point
│   ├── asgi.py                             # ASGI entry point (for async)
│   └── celery.py                           # Celery configuration (optional)
│
├── apps/                                   # Django apps (separated by feature)
│   │
│   ├── users/                              # User management app
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── models.py                       # User, Client models
│   │   ├── views.py                        # User endpoints (login, create, update, delete)
│   │   ├── serializers.py                  # DRF serializers
│   │   ├── urls.py                         # User app routes
│   │   ├── permissions.py                  # Custom permissions
│   │   ├── services.py                     # User business logic
│   │   └── admin.py                        # Django admin
│   │
│   ├── letters/                            # Letter management app
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── models.py                       # Letter, Category models
│   │   ├── views.py                        # Letter endpoints (generate, get, delete, list)
│   │   ├── serializers.py                  # DRF serializers
│   │   ├── urls.py                         # Letter app routes
│   │   ├── services.py                     # Letter generation logic
│   │   ├── tasks.py                        # Celery tasks (async operations)
│   │   ├── filters.py                      # Query filters
│   │   └── admin.py                        # Django admin
│   │
│   ├── chat/                               # Chat/editing app
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── models.py                       # ChatSession, Message models
│   │   ├── views.py                        # Chat endpoints
│   │   ├── serializers.py                  # DRF serializers
│   │   ├── urls.py                         # Chat routes
│   │   ├── services.py                     # Chat logic
│   │   ├── tasks.py                        # Async chat processing
│   │   └── admin.py                        # Django admin
│   │
│   ├── archive/                            # Archive/PDF app
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── models.py                       # Archive, PDFLog models
│   │   ├── views.py                        # Archive endpoints
│   │   ├── serializers.py                  # DRF serializers
│   │   ├── urls.py                         # Archive routes
│   │   ├── services.py                     # PDF generation, Google Drive upload
│   │   ├── tasks.py                        # Background PDF generation
│   │   └── admin.py                        # Django admin
│   │
│   └── api/                                # API utilities app
│       ├── __init__.py
│       ├── views.py                        # Generic API views (health, status)
│       ├── serializers.py                  # Generic serializers
│       ├── permissions.py                  # DRF permission classes
│       ├── authentication.py               # JWT authentication
│       ├── pagination.py                   # DRF pagination classes
│       ├── throttling.py                   # Rate limiting
│       └── renderers.py                    # Custom JSON renderers
│
├── core/                                   # Core/shared utilities
│   ├── __init__.py
│   ├── models.py                           # Base models (timestamps, soft delete)
│   ├── managers.py                         # Custom queryset managers
│   ├── exceptions.py                       # Custom exceptions
│   ├── decorators.py                       # Custom decorators
│   ├── utils.py                            # Helper functions
│   ├── constants.py                        # Constants/enums
│   ├── middleware.py                       # Custom middleware
│   └── logging.py                          # Logging configuration (like src/utils/log_manager.py)
│
├── services/                               # External services
│   ├── __init__.py
│   ├── google_sheets.py                    # Google Sheets service (replaces src/services/google_services.py)
│   ├── google_drive.py                     # Google Drive service (replaces src/services/drive_logger.py)
│   ├── openai_service.py                   # OpenAI/GPT service (replaces src/services/letter_generator.py)
│   ├── pdf_service.py                      # PDF generation (replaces src/services/enhanced_pdf_service.py)
│   └── cache_service.py                    # Caching logic
│
├── tests/                                  # Test suite
│   ├── __init__.py
│   ├── conftest.py                         # Pytest fixtures
│   ├── factories.py                        # Test factories
│   ├── test_api.py                         # API endpoint tests
│   │
│   ├── users/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   ├── test_services.py
│   │   └── test_permissions.py
│   │
│   ├── letters/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   ├── test_generation.py
│   │   └── test_services.py
│   │
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_views.py
│   │
│   └── archive/
│       ├── __init__.py
│       ├── test_models.py
│       └── test_views.py
│
├── static/                                 # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                                  # User uploaded files
│   └── letters/
│
├── logs/                                   # Application logs
│   ├── app.log
│   └── archive/
│
└── docs/                                   # Documentation
    ├── API.md
    ├── SETUP.md
    └── DEPLOYMENT.md
```

---

## Key Files & Migrations

### 1. config/settings.py
```python
# Replace src/config/settings.py with Django settings

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'django_filters',
    'django_cors_headers',
    'rest_framework_simplejwt',
    'drf_spectacular',  # API documentation

    # Local apps
    'apps.users',
    'apps.letters',
    'apps.chat',
    'apps.archive',
    'apps.api',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django_cors_headers.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.LoggingMiddleware',  # Custom logging middleware
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Use PostgreSQL in production
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.api.pagination.CustomPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
}
```

### 2. apps/users/models.py
```python
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.models import TimeStampedModel

class Client(TimeStampedModel):
    """Client organization"""
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'clients'
        verbose_name_plural = 'Clients'

    def __str__(self):
        return self.name

class CustomUser(AbstractUser, TimeStampedModel):
    """Extended user model"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='users')
    sheet_id = models.CharField(max_length=255)
    google_drive_id = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[('user', 'User'), ('admin', 'Admin')],
        default='user'
    )
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='inactive'
    )

    class Meta:
        db_table = 'users'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email
```

### 3. apps/letters/models.py
```python
from django.db import models
from django.contrib.auth import get_user_model
from core.models import TimeStampedModel

User = get_user_model()

class Letter(TimeStampedModel):
    """Letter model"""
    id = models.CharField(max_length=50, primary_key=True)  # LET-YYYYMMDD-XXXXX
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='letters')
    category = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    is_first_contact = models.BooleanField(default=False)

    # Status tracking
    review_status = models.CharField(
        max_length=50,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_letters')
    review_notes = models.TextField(blank=True)

    # Archive/Drive
    pdf_url = models.URLField(blank=True)
    drive_file_id = models.CharField(max_length=255, blank=True)

    # Metadata
    token_usage = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        db_table = 'letters'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['id']),
        ]

    def __str__(self):
        return f"{self.id} - {self.subject}"
```

### 4. apps/letters/views.py (DRF ViewSet)
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Letter
from .serializers import LetterSerializer, LetterDetailSerializer
from .services import LetterGenerationService
from .filters import LetterFilter

class LetterViewSet(viewsets.ModelViewSet):
    """
    Letter CRUD operations
    """
    serializer_class = LetterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LetterFilter
    search_fields = ['subject', 'recipient_name']
    ordering_fields = ['created_at', 'subject']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get letters for current user"""
        return Letter.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LetterDetailSerializer
        return LetterSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate new letter"""
        serializer = LetterGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = LetterGenerationService()
        letter = service.generate(
            user=request.user,
            **serializer.validated_data
        )

        return Response(
            LetterDetailSerializer(letter).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'])
    def delete_letter(self, request, pk=None):
        """Delete a letter"""
        letter = self.get_object()
        letter.delete()
        return Response(
            {'message': 'تم حذف الخطاب بنجاح'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['get'])
    def get_letter(self, request, pk=None):
        """Get letter by ID"""
        letter = self.get_object()
        serializer = self.get_serializer(letter)
        return Response(serializer.data)
```

### 5. config/urls.py
```python
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.users.views import UserViewSet, LoginView
from apps.letters.views import LetterViewSet
from apps.chat.views import ChatSessionViewSet
from apps.archive.views import ArchiveViewSet
from apps.api.views import HealthCheckView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'letters', LetterViewSet, basename='letter')
router.register(r'chat', ChatSessionViewSet, basename='chat')
router.register(r'archive', ArchiveViewSet, basename='archive')

urlpatterns = [
    path('admin/', admin.site.urls),

    # API routes
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/login/', LoginView.as_view(), name='login'),
    path('api/v1/health/', HealthCheckView.as_view(), name='health'),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

---

## Key Differences: Flask vs Django

| Feature | Flask | Django |
|---------|-------|--------|
| **Routing** | `@app.route()` | `urls.py` + ViewSets |
| **Models** | SQLAlchemy (optional) | Built-in ORM |
| **Authentication** | Manual JWT | `rest_framework_simplejwt` |
| **Serialization** | Manual JSON | DRF Serializers |
| **Validation** | Pydantic | DRF Validators |
| **Database** | Manual migrations | Auto migrations |
| **Testing** | Pytest | Django TestCase + Pytest |
| **Admin Panel** | None | Built-in Django Admin |
| **API Docs** | Manual | drf-spectacular (Swagger/OpenAPI) |
| **Async** | ASGI optional | Async views (3.1+) |
| **Caching** | Manual | Django cache framework |

---

## Migration Path from Flask

### Step 1: Create Django Project
```bash
django-admin startproject config .
python manage.py startapp users
python manage.py startapp letters
python manage.py startapp chat
python manage.py startapp archive
```

### Step 2: Move Models
- Convert Pydantic models to Django models
- Update relationships (ForeignKey, ManyToMany)
- Create migrations: `python manage.py makemigrations`

### Step 3: Move Services
- Services remain mostly the same
- Update database calls from SQLAlchemy to Django ORM
- Example:
  ```python
  # Flask/SQLAlchemy
  user = User.query.filter_by(email=email).first()

  # Django
  user = User.objects.get(email=email)
  ```

### Step 4: Convert Routes to Views
- Flask routes → Django ViewSets
- Request validation with DRF Serializers
- Return Response objects

### Step 5: Update Tests
- Use `django.test.TestCase` or `pytest-django`
- Use Django fixtures for test data

---

## Installation & Setup

### requirements.txt
```
Django==4.2.0
djangorestframework==3.14.0
django-filter==23.1
django-cors-headers==4.2.0
drf-spectacular==0.27.0
djangorestframework-simplejwt==5.3.0
python-dotenv==1.0.0
google-auth-oauthlib==1.1.0
google-cloud-storage==2.10.0
gspread==5.12.0
openai==1.3.0
celery==5.3.0
redis==5.0.0
pytest==7.4.0
pytest-django==4.5.2
psycopg2-binary==2.9.7  # PostgreSQL
```

### Setup Commands
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run tests
pytest

# Run Celery (in separate terminal)
celery -A config worker -l info
```

---

## Best Practices for Django

1. **Use ViewSets for CRUD** - `ModelViewSet` for automatic CRUD endpoints
2. **Leverage Django ORM** - Query optimization, select_related, prefetch_related
3. **Use Serializers for Validation** - Built-in validation, nested serializers
4. **Create Custom Permissions** - `BasePermission` for authorization
5. **Use Signals for Hooks** - Auto-update timestamps, send notifications
6. **Implement Queryset Methods** - Custom managers for common filters
7. **Use Celery for Async Tasks** - Background jobs, email, PDF generation
8. **Add API Documentation** - drf-spectacular for Swagger/OpenAPI
9. **Implement Pagination** - DRF pagination for large datasets
10. **Use Django Admin** - Built-in admin interface for data management

---

## Advantages of Django

✓ **Built-in Admin Panel** - CRUD interface without code
✓ **ORM** - Type-safe database queries
✓ **Migration System** - Version control for database schema
✓ **DRF** - Professional REST API framework
✓ **Authentication** - Built-in user model and permissions
✓ **Testing Tools** - Integrated testing framework
✓ **Documentation** - Comprehensive official docs
✓ **Scalability** - Used by Instagram, Spotify, Pinterest
✓ **Security** - CSRF, XSS, SQL injection protection built-in
✓ **Community** - Large community, many packages

---

## Considerations

- **Learning Curve** - More opinionated than Flask
- **Project Size** - Overkill for small projects
- **Flexibility** - Less flexible than Flask for custom solutions
- **Async** - Async support added in Django 3.1+ but not as mature as FastAPI

---

## Recommendation

**Use Django if:**
- You need a full-featured framework
- You want built-in admin panel
- You're building a large, scalable application
- You value convention over configuration
- You need comprehensive ORM

**Stick with Flask if:**
- You prefer lightweight and flexible approach
- You only need REST API (no admin panel needed)
- You want maximum customization
- Your project is small to medium sized

**Use FastAPI if:**
- You want modern async Python
- You need automatic API documentation
- You want type hints and validation
- You prefer simplicity with power

---

For this **AutomatingLetter** project, **Django is recommended** because:
✓ Need to manage multiple models (Users, Clients, Letters, etc.)
✓ Built-in admin for content management is useful
✓ DRF provides professional REST API
✓ Better for scaling to production
✓ Team collaboration is easier with conventions
