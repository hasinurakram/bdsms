from django.apps import AppConfig


class ResultsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'results'
    verbose_name = 'Results & Examinations'
    
    def ready(self):
        """Import signals when the app is ready"""
        import results.signals
