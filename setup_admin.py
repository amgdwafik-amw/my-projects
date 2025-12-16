import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oms_backend.settings')
django.setup()

from core.models import User

def create_admin():
    username = 'admin'
    password = 'admin'
    email = 'admin@example.com'
    
    try:
        if User.objects.filter(username=username).exists():
            u = User.objects.get(username=username)
            u.set_password(password)
            u.is_staff = True
            u.is_superuser = True
            u.role = User.Role.ADMIN
            u.save()
            print(f"Updated existing user '{username}' with password '{password}'")
        else:
            User.objects.create_superuser(username=username, email=email, password=password, role=User.Role.ADMIN)
            print(f"Created superuser '{username}' with password '{password}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_admin()
