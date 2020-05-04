from dataclasses import dataclass
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.db.transaction import atomic
from django.utils.timezone import now

from .models import Ledger
from .models import LedgerBalance
from .models import LedgerEntry
from .models import Transaction
from .models import TransactionRelatedObject
from .models import get_or_create_manual_transaction_kind
from .queries import validate_transaction


@dataclass
class Debit:
    amount: int

    def __post_init__(self):
        self.amount = -self.amount


@dataclass
class Credit:
    amount: int


@atomic
def create_transaction(
    user, evidence=(), ledger_entries=(), notes="", kind=None, posted_timestamp=None
):
    """
    Create a Transaction with LedgerEntries and TransactionRelatedObjects.

    This function is atomic and validates its input before writing to the DB.
    """
    # Lock the ledgers to which we are posting to serialize the update
    # of LedgerBalances.
    list(
        Ledger.objects.filter(
            id__in=(ledger_entry.ledger.id for ledger_entry in ledger_entries)
        )
        .order_by("id")  # Avoid deadlocks.
        .select_for_update()
    )

    if not posted_timestamp:
        posted_timestamp = now()

    validate_transaction(user, evidence, ledger_entries, notes, kind, posted_timestamp)

    transaction = Transaction.objects.create(
        created_by=user,
        notes=notes,
        posted_timestamp=posted_timestamp,
        kind=kind or get_or_create_manual_transaction_kind(),
    )

    for ledger_entry in ledger_entries:
        ledger_entry.transaction = transaction
        ledger_entry.amount = ledger_entry.amount.amount
        for related_object in evidence:
            content_type = ContentType.objects.get_for_model(related_object)
            num_updated = LedgerBalance.objects.filter(
                ledger=ledger_entry.ledger,
                related_object_content_type=content_type,
                related_object_id=related_object.id,
            ).update(balance=F("balance") + ledger_entry.amount)
            assert num_updated <= 1
            if num_updated == 0:
                # The first use of this evidence model in a ledger transaction.
                LedgerBalance.objects.create(
                    ledger=ledger_entry.ledger,
                    related_object_content_type=content_type,
                    related_object_id=related_object.id,
                    balance=ledger_entry.amount,
                )

    LedgerEntry.objects.bulk_create(ledger_entries)

    transaction_related_objects = [
        TransactionRelatedObject(related_object=piece, transaction=transaction)
        for piece in evidence
    ]
    TransactionRelatedObject.objects.bulk_create(transaction_related_objects)

    return transaction
