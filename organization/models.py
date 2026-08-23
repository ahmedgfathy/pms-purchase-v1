from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=30, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Section(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=30, unique=True)
    head = models.ForeignKey('EmployeeProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='led_sections')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class JobTitle(models.Model):
    name = models.CharField(max_length=120, unique=True)
    job_description = models.TextField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee')
    employee_no = models.CharField(max_length=20, unique=True)
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.PROTECT, related_name='employees')
    direct_manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')
    phone = models.CharField(max_length=30, blank=True)
    hire_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['employee_no']

    def __str__(self):
        return f"{self.employee_no} · {self.user.get_full_name() or self.user.username}"
