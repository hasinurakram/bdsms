from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'  # <- এখানে অবশ্যই পাথ ঠিক থাকতে হবে

    def ready(self):
        # Import signals to ensure they are registered on app startup
        from . import signals  # noqa: F401
