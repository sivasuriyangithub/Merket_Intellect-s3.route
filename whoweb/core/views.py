from graphene_django.views import GraphQLView
from sentry_sdk import start_transaction


class SentryEnabledGraphQLView(GraphQLView):
    def execute_graphql_request(
        self, request, data, query, variables, operation_name, show_graphiql=False
    ):
        operation_type = (
            self.get_backend(request)
            .document_from_string(self.schema, query)
            .get_operation_type(operation_name)
        )
        with start_transaction(op=operation_type, name=operation_name):
            return super().execute_graphql_request(
                request, data, query, variables, operation_name, show_graphiql
            )
