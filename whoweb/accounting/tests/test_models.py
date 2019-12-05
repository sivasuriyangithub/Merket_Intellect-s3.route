from __future__ import unicode_literals

from datetime import datetime
from decimal import Decimal as D

from django.test import TestCase

from whoweb.accounting.actions import Credit, Debit
from whoweb.accounting.actions import create_transaction
from whoweb.accounting.exceptions import ExistingLedgerEntriesException
from whoweb.accounting.exceptions import NoLedgerEntriesException
from whoweb.accounting.exceptions import TransactionBalanceException
from whoweb.accounting.models import LedgerEntry
from whoweb.accounting.models import Transaction
from whoweb.accounting.queries import validate_transaction
from whoweb.accounting.tests.factories import LedgerFactory
from whoweb.accounting.tests.factories import TransactionTypeFactory
from whoweb.accounting.tests.factories import UserFactory

RECONCILIATION_TYPE_NAME = "Recon"


class TestCreateTransaction(TestCase):
    def setUp(self):
        self.AMOUNT = D(100)
        self.user = UserFactory()

        self.accounts_receivable = LedgerFactory(name="Accounts Receivable")
        self.cash_unrecon = LedgerFactory(name="Cash (unreconciled)")
        self.cash_recon = LedgerFactory(name="Cash (reconciled)")
        self.revenue = LedgerFactory(name="Revenue", liability=False)
        self.recon_ttype = TransactionTypeFactory(name=RECONCILIATION_TYPE_NAME)

    def test_using_ledgers_for_reconciliation(self):
        """
        Test ledger behavior with a revenue reconciliation worked example.

        This test creates an Order and a CreditCardTransaction and, using the
        four Ledgers created in setUp, it makes all of the ledger entries that
        an Order and Transaction would be expected to have.  There are three,
        specifically: Revenue Recognition (credit: Revenue, debit:A/R), recording
        incoming cash (credit: A/R, debit: Cash (unreconciled)) and Reconciliation
        (credit: Cash (reconciled), debit: Cash (unreconciled)).

        In table form:

        Event                   | Accounts Receivable (unreconciled) | Revenue | Cash (unreconciled) | Cash (reconciled) | Evidence Models
        ----------------------- | ---------------------------------- | ------- | ------------------- | ----------------- | --------------------------------------------------------------
        Test is complete        | -$500                              | +$500   |                     |                   | `Order`
        Patient pays            | +$500                              |         | -$500               |                   | `CreditCardTransaction`
        Payments are reconciled |                                    |         | +$500               | -$500             | both `Order` and `CreditCardTransaction`
        """  # nopep8

        # Add an entry debiting AR and crediting Revenue: this entry should
        # reference the Order.
        create_transaction(
            self.user,
            evidence=[],
            ledger_entries=[
                LedgerEntry(ledger=self.revenue, amount=Credit(self.AMOUNT)),
                LedgerEntry(ledger=self.accounts_receivable, amount=Debit(self.AMOUNT)),
            ],
        )

        # Assert that the correct entries were created.
        assert LedgerEntry.objects.count() == 2
        assert Transaction.objects.count() == 1

        # Add an entry crediting "A/R" and debiting "Cash (unreconciled)": this
        # entry should reference the CreditCardTransaction.
        create_transaction(
            self.user,
            evidence=[],
            ledger_entries=[
                LedgerEntry(
                    ledger=self.accounts_receivable, amount=Credit(self.AMOUNT)
                ),
                LedgerEntry(ledger=self.cash_unrecon, amount=Debit(self.AMOUNT)),
            ],
        )

        # Assert that the correct entries were created
        self.assertEqual(LedgerEntry.objects.count(), 4)
        self.assertEqual(Transaction.objects.count(), 2)

        # Add an entry crediting "Cash (Unreconciled)" and debiting "Cash
        # (Reconciled)": this entry should reference both an Order and
        # a CreditCardTransaction.
        create_transaction(
            self.user,
            evidence=[],
            ledger_entries=[
                LedgerEntry(ledger=self.cash_unrecon, amount=Credit(self.AMOUNT)),
                LedgerEntry(ledger=self.cash_recon, amount=Debit(self.AMOUNT)),
            ],
            kind=self.recon_ttype,
        )

        # Assert that the correct entries were created.
        self.assertEqual(LedgerEntry.objects.count(), 6)
        self.assertEqual(Transaction.objects.count(), 3)

    def test_setting_posted_timestamp(self):
        POSTED_DATETIME = datetime(2016, 2, 7, 11, 59)

        txn_recognize = create_transaction(
            self.user,
            evidence=[],
            ledger_entries=[
                LedgerEntry(ledger=self.revenue, amount=Credit(self.AMOUNT)),
                LedgerEntry(ledger=self.accounts_receivable, amount=Debit(self.AMOUNT)),
            ],
            posted_timestamp=POSTED_DATETIME,
        )

        self.assertEqual(txn_recognize.posted_timestamp, POSTED_DATETIME)

    def test_debits_not_equal_to_credits(self):
        with self.assertRaises(TransactionBalanceException):
            validate_transaction(
                self.user,
                ledger_entries=[
                    LedgerEntry(ledger=self.revenue, amount=Credit(self.AMOUNT)),
                    LedgerEntry(
                        ledger=self.accounts_receivable, amount=Debit(self.AMOUNT + 2)
                    ),
                ],
            )

    def test_no_ledger_entries(self):
        with self.assertRaises(NoLedgerEntriesException):
            validate_transaction(self.user)


class TestExistingLedgerEntriesException(TestCase):
    def setUp(self):
        self.amount = D(100)
        self.user = UserFactory()

        self.accounts_receivable = LedgerFactory(name="Accounts Receivable")
        self.cash = LedgerFactory(name="Cash")

    def test_with_existing_ledger_entry(self):
        existing_transaction = create_transaction(
            self.user,
            ledger_entries=[
                LedgerEntry(
                    ledger=self.accounts_receivable, amount=Credit(self.amount)
                ),
                LedgerEntry(ledger=self.accounts_receivable, amount=Debit(self.amount)),
            ],
        )

        with self.assertRaises(ExistingLedgerEntriesException):
            create_transaction(
                self.user, ledger_entries=list(existing_transaction.entries.all())
            )


class TestCreditAndDebit(TestCase):
    """
    Test that `credit` and `debit` return the correctly signed amounts.
    """

    AMOUNT = D(100)

    def assertPositive(self, amount):
        self.assertGreaterEqual(amount, 0)

    def assertNegative(self, amount):
        self.assertLess(amount, 0)


class TestRounding(TestCase):
    def _create_transaction_and_compare_to_amount(self, amount, comparison_amount=None):
        ledger1 = LedgerFactory()
        ledger2 = LedgerFactory()
        transaction = create_transaction(
            UserFactory(),
            ledger_entries=[
                LedgerEntry(ledger=ledger1, amount=amount),
                LedgerEntry(ledger=ledger2, amount=-amount),
            ],
        )

        entry1 = transaction.entries.get(ledger=ledger1)
        entry2 = transaction.entries.get(ledger=ledger2)
        if comparison_amount:
            self.assertNotEqual(entry1.amount, amount)
            self.assertEqual(entry1.amount, comparison_amount)
            self.assertNotEqual(entry2.amount, -amount)
            self.assertEqual(-entry2.amount, comparison_amount)
        else:
            self.assertEqual(entry1.amount, amount)
            self.assertEqual(entry2.amount, -amount)
