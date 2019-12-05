from __future__ import unicode_literals
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from whoweb.accounting.actions import create_transaction
from whoweb.accounting.actions import Credit
from whoweb.accounting.actions import Debit
from whoweb.accounting.models import Ledger
from whoweb.accounting.models import LedgerEntry
from whoweb.accounting.models import TransactionKind


class UserFactory(factory.DjangoModelFactory):
    """
    Factory for django.contrib.auth.get_user_model()

    `capone` relies on `django.contrib.auth` because each `Transaction` is
    attached to the `User` who created it.  Therefore, we can't just use a stub
    model here with, say, only a name field.
    """

    class Meta:
        model = get_user_model()

    email = username = factory.Sequence(lambda n: "TransactionUser #%s" % n)


class LedgerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Ledger

    liability = True
    name = factory.Sequence(lambda n: "Test Ledger {}".format(n))
    account_code = factory.Sequence(lambda n: n)


class TransactionTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = TransactionKind

    name = factory.Sequence(lambda n: "Transaction Type %s" % n)


def TransactionFactory(
    user=None,
    evidence=None,
    ledger_entries=None,
    notes="",
    type=None,
    posted_timestamp=None,
):
    """
    Factory for creating a Transaction

    Instead of inheriting from DjangoModelFactory, TransactionFactory is
    a method made to look like a factory call because the creation and
    validation of Transactions is handeled by `create_transaction`.
    """
    if user is None:
        user = UserFactory()

    if evidence is None:
        evidence = []

    if ledger_entries is None:
        ledger = LedgerFactory()
        amount = Decimal("100")
        ledger_entries = [
            LedgerEntry(ledger=ledger, amount=Debit(amount)),
            LedgerEntry(ledger=ledger, amount=Credit(amount)),
        ]

    return create_transaction(
        user,
        evidence=evidence,
        ledger_entries=ledger_entries,
        notes=notes,
        type=type or TransactionTypeFactory(),
        posted_timestamp=posted_timestamp,
    )
