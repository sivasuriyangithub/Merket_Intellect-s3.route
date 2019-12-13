import graphene
import graphql_jwt
from django.conf import settings
from graphene_django.debug import DjangoDebug
from graphql_jwt.decorators import login_required

from whoweb.users.schema import Query as UsersQuery
from whoweb.users.mutations import Mutation as UsersMutation


class Viewer(UsersQuery, graphene.ObjectType):
    class Meta:
        interfaces = [graphene.relay.Node]

    debug = graphene.Field(DjangoDebug, name="_debug") if settings.DEBUG else None


class Query(graphene.ObjectType):
    viewer = graphene.Field(Viewer, token=graphene.String(required=True))

    @login_required
    def resolve_viewer(self, info, **kwargs):
        return info.context.user


class Mutation(UsersMutation, graphene.ObjectType):
    token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    refresh_token = graphql_jwt.relay.Refresh.Field()
    verify_token = graphql_jwt.relay.Verify.Field() if settings.DEBUG else None
    # Long running refresh tokens
    # revoke_token = graphql_jwt.relay.Revoke.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
