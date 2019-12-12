from django.contrib.auth import get_user_model


def get_user_by_natural_key(username):
    User = get_user_model()
    try:
        return User.objects.get(email=username)
    except User.DoesNotExist:
        return None
