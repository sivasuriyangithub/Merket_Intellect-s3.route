import graphene
import graphql_jwt
from django.conf import settings
from graphene_django.debug import DjangoDebug
from graphql_jwt.decorators import login_required

from whoweb.users.schema import Query as UsersQuery


class Viewer(UsersQuery, graphene.ObjectType):
    class Meta:
        interfaces = [graphene.relay.Node]

    debug = graphene.Field(DjangoDebug, name="_debug") if settings.DEBUG else None


class Query(graphene.ObjectType):
    viewer = graphene.Field(Viewer, token=graphene.String(required=True))
    # eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6InphY2hAd2hva25vd3MuY29tIiwiZXhwIjoxNTc2MTE4NjI5LCJvcmlnSWF0IjoxNTc2MTE4MzI5fQ.YEX2hLOnlHTSUHtMA6hF2euD1QanzY25eywLNfhhFkQ

    @login_required
    def resolve_viewer(self, info, **kwargs):
        return info.context.user


class Mutation(graphene.ObjectType):
    token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.relay.Verify.Field()
    refresh_token = graphql_jwt.relay.Refresh.Field()
    # Long running refresh tokens
    revoke_token = graphql_jwt.relay.Revoke.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
