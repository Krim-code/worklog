from django.contrib import admin
from django.urls import path
from django.db.models import Sum, F
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta, date

from .models import Worker, WorkType, WorkEntry


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "telegram_id", "username", "is_active", "last_seen", "created_at")
    list_filter = ("is_active",)
    search_fields = ("full_name", "username", "telegram_id")
    readonly_fields = ("created_at", "updated_at", "joined_at", "last_seen")
    ordering = ("-is_active", "full_name")


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "unit", "is_active", "default_rate")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    list_editable = ("is_active", "default_rate")


@admin.register(WorkEntry)
class WorkEntryAdmin(admin.ModelAdmin):
    list_display = ("work_date", "worker", "work_type", "quantity", "created_at")
    list_filter = ("work_date", "work_type")
    search_fields = ("worker__full_name", "worker__username", "comment")
    date_hierarchy = "work_date"
    autocomplete_fields = ("worker", "work_type")
    readonly_fields = ("created_at", "updated_at")
    change_list_template = "admin/worklog/workentry/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("analytics/", self.admin_site.admin_view(self.analytics_view), name="worklog_workentry_analytics"),
        ]
        return custom + urls

    def analytics_view(self, request):
        # --- параметры периода ---
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        start_str = request.GET.get("start")
        end_str = request.GET.get("end")
        try:
            start = date.fromisoformat(start_str) if start_str else today - timedelta(days=6)
            end = date.fromisoformat(end_str) if end_str else today
        except ValueError:
            start, end = today - timedelta(days=6), today

        qs = WorkEntry.objects.filter(work_date__range=(start, end))

        # --- сводка за период ---
        total_qty = qs.aggregate(total=Sum("quantity"))["total"] or 0

        # — по дням (для line chart)
        by_day = (
            qs.values("work_date")
            .annotate(total=Sum("quantity"))
            .order_by("work_date")
        )

        # чтобы на графике были нули для отсутствующих дней
        totals_map = {row["work_date"]: float(row["total"]) for row in by_day}

        days_labels = []
        days_values = []
        d = start
        while d <= end:
            days_labels.append(d.isoformat())
            days_values.append(totals_map.get(d, 0.0))
            d += timedelta(days=1)

        # — топ работников
        top_workers = (
            qs.values("worker__full_name")
              .annotate(total=Sum("quantity"))
              .order_by("-total")[:10]
        )
        workers_labels = [x["worker__full_name"] for x in top_workers]
        workers_values = [float(x["total"]) for x in top_workers]

        # — по типам работ (bar)
        by_type = (
            qs.values(name=F("work_type__name"), unit=F("work_type__unit"))
              .annotate(total=Sum("quantity"))
              .order_by("-total")
        )
        types_labels = [f'{x["name"]} ({x["unit"]})' for x in by_type]
        types_values = [float(x["total"]) for x in by_type]

        # — сводка «сегодня»
        today_qs = WorkEntry.objects.filter(work_date=today)
        today_total = today_qs.aggregate(total=Sum("quantity"))["total"] or 0
        today_workers = today_qs.values("worker").distinct().count()
        today_types = today_qs.values("work_type").distinct().count()

        context = {
            **self.admin_site.each_context(request),
            "title": "Аналитика работ",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total_qty": float(total_qty),
            "days_labels": days_labels,
            "days_values": days_values,
            "workers_labels": workers_labels,
            "workers_values": workers_values,
            "types_labels": types_labels,
            "types_values": types_values,
            "today_total": float(today_total),
            "today_workers": today_workers,
            "today_types": today_types,
            "model_opts": self.model._meta,
        }
        from django.shortcuts import render
        return render(request, "admin/worklog/analytics.html", context)