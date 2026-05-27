from accounts.infrastructure.models import User

user = User.objects.get(username='admin')
user.set_password('admin123')
user.save()
print('Password set for admin')
