from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter
from rest_framework_simplejwt.views import TokenObtainSlidingView
from slugify import slugify

from whoweb.contrib.rest_framework.permissions import ObjectPermissions, IsSuperUser
from whoweb.users.models import Seat, DeveloperKey, Group, UserProfile
from whoweb.users.serializers import (
    SeatSerializer,
    DeveloperKeySerializer,
    NetworkSerializer,
    UserSerializer,
    AuthManagementSerializer,
    ImpersonatedTokenObtainSlidingSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class NetworkViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"
    queryset = Group.objects.all()
    serializer_class = NetworkSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class SeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class DeveloperKeyViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    lookup_field = "public_id"
    queryset = DeveloperKey.objects.all()
    serializer_class = DeveloperKeySerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class ImpersonatedTokenObtainSlidingView(TokenObtainSlidingView):
    """
    Takes a set of user credentials and returns a sliding JSON web token to
    prove the authentication of those credentials.
    """

    serializer_class = ImpersonatedTokenObtainSlidingSerializer
    permission_classes = [IsSuperUser]
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES


class ManageUserAuthenticationAPIView(APIView):
    permission_classes = [IsSuperUser]
    serializer_class = AuthManagementSerializer

    def post(self, request, **kwargs):
        serializer = AuthManagementSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        seat: Seat = serializer.validated_data.get("seat")
        if not seat:
            xperweb_id = serializer.validated_data.get("xperweb_id")
            email = serializer.validated_data.get("email")
            first_name = serializer.validated_data.get("first_name")
            last_name = serializer.validated_data.get("last_name")
            group_id = serializer.validated_data.get("group_id")
            group_name = serializer.validated_data.get("group_name") or group_id

            profile, _ = UserProfile.get_or_create(
                xperweb_id=xperweb_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            group, _ = Group.objects.get_or_create(
                slug=slugify(group_id), defaults={"name": group_name}
            )
            seat, _ = group.get_or_add_user(
                user=profile.user, display_name=profile.user.get_full_name()
            )
        user: User = seat.user
        user.set_password(serializer.validated_data["password"])
        user.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
