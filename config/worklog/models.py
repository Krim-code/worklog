from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Worker(TimeStamped):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        base = self.full_name or f"#{self.pk}"
        return f"{base} [{self.telegram_id}]"

    class Meta:
        verbose_name = _("Работник")
        verbose_name_plural = _("Работники")
        ordering = ["-is_active", "full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["is_active"]),
        ]


class WorkType(TimeStamped):
    code = models.SlugField(max_length=64, unique=True)            # например: bricks, paint, wiring
    name = models.CharField(max_length=128)                        # Человеческое название
    unit = models.CharField(max_length=32, default="шт")           # шт, м2, м.п., ч
    is_active = models.BooleanField(default=True)
    default_rate = models.DecimalField(                            # если пригодится для денег
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        verbose_name = _("Тип работы")
        verbose_name_plural = _("Типы работ")
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]


class WorkEntry(TimeStamped):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT, related_name="entries")
    work_type = models.ForeignKey(WorkType, on_delete=models.PROTECT, related_name="entries")
    work_date = models.DateField(db_index=True, default=timezone.localdate)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(0)], help_text="Сколько сделали"
    )
    comment = models.TextField(blank=True, null=True)

    # полезно для аудита бота
    source_chat_id = models.BigIntegerField(blank=True, null=True)
    source_message_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        verbose_name = _("Запись о работе")
        verbose_name_plural = _("Записи о работах")
        ordering = ["-work_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["worker", "work_type", "work_date"],
                name="uniq_worker_worktype_day",
            )
        ]
        indexes = [
            models.Index(fields=["work_date", "worker"]),
            models.Index(fields=["worker", "created_at"]),
        ]

    def __str__(self):
        return f"{self.work_date} · {self.worker} · {self.work_type} = {self.quantity} {self.work_type.unit}"
