from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps

def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(role, profile_model):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not profile_model.objects.filter(user=request.user).exists():
                return redirect('/login/')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def patient_required(view_func):
    from hospital.models import Patient
    return role_required("patient", Patient)(view_func)


def doctor_required(view_func):
    from hospital.models import Doctor
    return role_required("doctor", Doctor)(view_func)
