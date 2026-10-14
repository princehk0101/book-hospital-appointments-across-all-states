from django.contrib import admin
from .models import District, Hospital, Doctor, Patient, Appointment, Treatment, Availability

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "is_active", "is_sample")
    list_filter = ("district", "is_active", "is_sample")
    search_fields = ("name", "district__name", "address")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "hospital", "department", "specialization", "is_sample")
    list_filter = ("hospital__district", "hospital", "department", "is_sample")
    search_fields = ("user__first_name", "user__last_name", "hospital__name", "department")

admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(Treatment)
admin.site.register(Availability)
