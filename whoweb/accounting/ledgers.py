from whoweb.accounting.models import Ledger


def wkcredits_sold_ledger():

    return Ledger.objects.get_or_create(
        name="WhoKnows Customer Credit Sales",
        account_code=100,
        liability=False,
        defaults=dict(description="Records all credit sales."),
    )[0]


def wkcredits_liability_ledger():

    return Ledger.objects.get_or_create(
        name="WhoKnows Customer Credits Outstanding",
        account_code=200,
        liability=True,
        defaults=dict(
            description="Records credits purchased but not used across all users."
        ),
    )[0]


def wkcredits_fulfilled_ledger():

    return Ledger.objects.get_or_create(
        name="WhoKnows Customer Credits Fulfilled",
        account_code=300,
        liability=False,
        defaults=dict(description="Records credits used across all users."),
    )[0]


def wkcredits_expired_ledger():

    return Ledger.objects.get_or_create(
        name="WhoKnows Customer Credits Expired",
        account_code=400,
        liability=False,
        defaults=dict(description="Records all user credits expired."),
    )[0]
