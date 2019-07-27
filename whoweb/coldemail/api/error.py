from .utils import python_2_unicode_compatible


@python_2_unicode_compatible
class ColdEmailError(Exception):
    def __init__(
        self,
        message=None,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
    ):
        super(ColdEmailError, self).__init__(message)

        if http_body and hasattr(http_body, "decode"):
            try:
                http_body = http_body.decode("utf-8")
            except BaseException:
                http_body = "<Could not decode body as utf-8.>"

        self._message = message
        self.http_body = http_body
        self.http_status = http_status
        self.json_body = json_body
        self.headers = headers or {}
        self.request_id = self.headers.get("request-id", None)

    def __str__(self):
        msg = self._message or "<empty message>"
        if self.request_id is not None:
            return u"Request {0}: {1}".format(self.request_id, msg)
        else:
            return msg

    def __repr__(self):
        return "%s(message=%r, http_status=%r, request_id=%r)" % (
            self.__class__.__name__,
            self._message,
            self.http_status,
            self.request_id,
        )


class APIError(ColdEmailError):
    pass


class RateLimitError(ColdEmailError):
    pass


class InvalidRequestError(ColdEmailError):
    def __init__(
        self,
        message,
        param,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
    ):
        super(InvalidRequestError, self).__init__(
            message, http_body, http_status, json_body, headers
        )
        self.param = param


class AuthenticationError(ColdEmailError):
    pass


class PaymentError(ColdEmailError):
    def __init__(
        self,
        message,
        param,
        code,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
    ):
        super(ColdEmailError, self).__init__(
            message, http_body, http_status, json_body, headers
        )
        self.param = param
        self.code = code


class PermissionError(ColdEmailError):
    pass
