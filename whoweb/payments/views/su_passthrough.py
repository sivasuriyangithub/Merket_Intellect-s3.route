from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.users.models import Seat, UserProfile
from ..models import BillingAccountMember
from ..serializers import (
    AdminBillingSeatSerializer,
    AdminBillingAccountSerializer,
    BillingAccountMemberSerializer,
)


class AdminBillingSeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingSeatSerializer
    permission_classes = [IsSuperUser]
    schema = None


class AdminBillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingAccountSerializer
    permission_classes = [IsSuperUser]
    schema = None


@api_view(
    ["GET",]
)
@staff_member_required
def find_billing_seat_by_xperweb_id(request, xperweb_id):
    member = BillingAccountMember.objects.filter(
        Q(user__profile__xperweb_id=xperweb_id) | Q(user__username=xperweb_id)
    ).first()
    if not member:
        raise Http404("Member not found with id %s" % xperweb_id)
    serializer = BillingAccountMemberSerializer(member, context={"request": request})
    return Response(serializer.data)
