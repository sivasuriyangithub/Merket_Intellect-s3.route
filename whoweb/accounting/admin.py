from django.contrib import admin
from .models import Ledger, Transaction, TransactionKind, LedgerEntry

# Register your models here.

admin.site.register(Ledger, admin.ModelAdmin)
admin.site.register(LedgerEntry, admin.ModelAdmin)
admin.site.register(Transaction, admin.ModelAdmin)
admin.site.register(TransactionKind, admin.ModelAdmin)
