from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)

    def __str__(self):
        return self.name
