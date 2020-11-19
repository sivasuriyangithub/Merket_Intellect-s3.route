import graphene
import graphql_jwt
import jwt
from django.conf import settings
from graphene_django.debug import DjangoDebug
from graphene_django.rest_framework.mutation import SerializerMutation
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainSlidingSerializer as SimpleSlidingSerializer,
    TokenRefreshSlidingSerializer as SimpleRefreshSerializer,
)
from rest_framework_simplejwt.tokens import SlidingToken

from whoweb.payments.schema import Query as PaymentsQuery
from whoweb.search.mutations import Mutation as SearchMutation
from whoweb.search.schema import Query as SearchQuery
from whoweb.users.mutations import Mutation as UsersMutation
from whoweb.users.schema import Query as UsersQuery
from whoweb.campaigns.schema import Query as CampaignsQuery
from whoweb.campaigns.mutations import Mutation as CampaignMutation


class Query(
    UsersQuery, SearchQuery, PaymentsQuery, CampaignsQuery, graphene.ObjectType
):
    debug = graphene.Field(DjangoDebug, name="_debug") if settings.DEBUG else None


class TokenObtainSlidingSerializer(SimpleSlidingSerializer):
    token = serializers.CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(write_only=True)

    def create(self, validated_data):
        return validated_data


class TokenRefreshSlidingSerializer(SimpleRefreshSerializer):
    def validate(self, attrs):
        from rest_framework_simplejwt.state import token_backend
        from rest_framework_simplejwt.settings import api_settings

        # Verify all but exp, then proceed with SlidingSerializerSuper
        try:
            jwt.decode(
                attrs["token"],
                token_backend.verifying_key,
                algorithms=[token_backend.algorithm],
                verify=True,
                audience=token_backend.audience,
                issuer=token_backend.issuer,
                options={
                    "verify_aud": token_backend.audience is not None,
                    "verify_exp": False,  # diff
                },
            )
        except TokenBackendError:
            raise TokenError(_("Token is invalid or expired"))
        token = SlidingToken(attrs["token"], verify=False)  # diff
        token.check_exp(api_settings.SLIDING_TOKEN_REFRESH_EXP_CLAIM)
        # Update the "exp" claim
        token.set_exp()

        return {"token": str(token)}

    def create(self, validated_data):
        return validated_data


class ObtainJSONWebToken(SerializerMutation):
    class Meta:
        serializer_class = TokenObtainSlidingSerializer


class RereshSlidingJSONWebToken(SerializerMutation):
    class Meta:
        serializer_class = TokenRefreshSlidingSerializer


class Mutation(UsersMutation, SearchMutation, CampaignMutation, graphene.ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    refresh_token = RereshSlidingJSONWebToken.Field()
    verify_token = graphql_jwt.relay.Verify.Field() if settings.DEBUG else None


schema = graphene.Schema(query=Query, mutation=Mutation)
