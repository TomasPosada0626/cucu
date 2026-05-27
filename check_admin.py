from accounts.infrastructure.models import User

user = User.objects.get(username='admin')
print(f"Email: {user.email}")
if not user.email:
    user.email = 'admin@example.com'
    user.save()
    print("Email updated to admin@example.com")
