from django.contrib import admin

from .models import SupportComment, SupportTicket, SupportTicketUpvote


class SupportCommentInline(admin.TabularInline):
    model = SupportComment
    extra = 0
    readonly_fields = ('user', 'created_at')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'category', 'status', 'is_highlighted', 'upvotes', 'created_at')
    list_filter = ('status', 'is_highlighted', 'category', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    inlines = [SupportCommentInline]


@admin.register(SupportComment)
class SupportCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'created_at')
    search_fields = ('ticket__title', 'comment', 'user__username')
    list_filter = ('created_at',)


@admin.register(SupportTicketUpvote)
class SupportTicketUpvoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'created_at')
    search_fields = ('ticket__title', 'user__username')
    list_filter = ('created_at',)
