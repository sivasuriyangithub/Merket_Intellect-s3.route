from django.contrib import admin
from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Ledger, Transaction, TransactionKind, LedgerEntry, LedgerBalance


class LedgerBalanceInline(GenericTabularInline):
    model = LedgerBalance
    ct_field = "related_object_content_type"
    ct_fk_field = "related_object_id"
    fields = ("ledger", "balance", "created_at", "modified_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class LedgerEntryInline(TabularInline):
    model = LedgerEntry


class TransactionInline(TabularInline):
    model = Transaction
    inlines = [LedgerEntryInline]


class LedgerModelAdmin(admin.ModelAdmin):
    model = Ledger
    inlines = [LedgerEntryInline]


class TransactionModelAdmin(admin.ModelAdmin):
    model = Transaction
    inlines = [LedgerEntryInline]
    list_display = (
        "transaction_id",
        "created_by",
        "posted_timestamp",
    )
    search_fields = ["created_by__username", "created_by__email", "transaction_id"]
    list_per_page = 10


# admin.site.register(LedgerEntry, admin.ModelAdmin)
admin.site.register(Ledger, LedgerModelAdmin)
admin.site.register(Transaction, TransactionModelAdmin)
admin.site.register(TransactionKind, admin.ModelAdmin)
