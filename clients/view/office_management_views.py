from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from clients.models import Company, UserProfile
import json

def office_management(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    users = User.objects.all()
    return render(request, 'office_management.html', {'users': users})

@csrf_exempt
def create_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            is_staff = data.get('is_staff', False)

            if not username or not email or not password:
                return JsonResponse({'success': False, 'error': 'Missing required fields.'})

            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Username already exists.'})
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists.'})

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
                is_active=True
            )

            # Assign the superuser's company to the new user
            superuser_profile = UserProfile.objects.filter(user=request.user).first()
            if superuser_profile and superuser_profile.company:
                UserProfile.objects.create(user=user, company=superuser_profile.company)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def delete_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return JsonResponse({'success': False, 'error': 'Cannot delete superuser.'})
            user.delete()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def get_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            user = User.objects.get(id=user_id)
            return JsonResponse({
                'success': True,
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff
                }
            })
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def update_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            email = data.get('email')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            is_staff = data.get('is_staff', False)
            new_password = data.get('new_password')

            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required.'})

            user = User.objects.get(id=user_id)
            if user.is_superuser and not is_staff:
                return JsonResponse({'success': False, 'error': 'Cannot remove staff status from superuser.'})

            if User.objects.filter(email=email).exclude(id=user_id).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists.'})

            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            if new_password:
                user.set_password(new_password)
            user.save()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})