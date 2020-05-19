import graphene
import graphql_jwt
from django.conf import settings
from graphene_django.debug import DjangoDebug
from graphql_jwt.decorators import login_required

from whoweb.users.schema import Query as UsersQuery, SeatNode
from whoweb.search.schema import Query as SearchQuery
from whoweb.payments.schema import Query as PaymentsQuery
from whoweb.users.mutations import Mutation as UsersMutation


class Viewer(UsersQuery, SearchQuery, PaymentsQuery, graphene.ObjectType):
    class Meta:
        interfaces = [graphene.relay.Node]

    debug = graphene.Field(DjangoDebug, name="_debug") if settings.DEBUG else None


class Query(graphene.ObjectType):
    viewer = graphene.Field(
        Viewer, token=graphene.String(required=True), seat=graphene.ID(required=False)
    )

    @login_required
    def resolve_viewer(self, info, seat=None, **kwargs):
        if seat is not None:
            seat = SeatNode.get_node(info, seat)
        if not hasattr(info.context, "seat"):
            info.context.seat = seat
        return info.context.user


class ViewerMutation(UsersMutation, graphene.ObjectType):
    class Meta:
        interfaces = [graphene.relay.Node]


class Mutation(graphene.ObjectType):
    token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    refresh_token = graphql_jwt.relay.Refresh.Field()
    verify_token = graphql_jwt.relay.Verify.Field() if settings.DEBUG else None
    viewer = graphene.Field(ViewerMutation, token=graphene.String(required=True))

    # Long running refresh tokens
    # revoke_token = graphql_jwt.relay.Revoke.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
