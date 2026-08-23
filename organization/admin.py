from django.contrib import admin

from .models import Department, EmployeeProfile, JobTitle, Section


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'head')


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_no', 'user', 'job_title', 'department', 'section', 'direct_manager')
    list_filter = ('department', 'section', 'job_title')
    search_fields = ('employee_no', 'user__username', 'user__first_name', 'user__last_name')
