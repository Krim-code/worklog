import random
from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from worklog.models import Worker, WorkType, WorkEntry


class Command(BaseCommand):
    help = "Наполняет демо-данными: workers, entries"

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=10)
        parser.add_argument("--days", type=int, default=7)
        parser.add_argument("--entries-per-day", type=int, default=2)

    def handle(self, *args, **opts):
        fake = Faker("ru_RU")
        workers_count = opts["workers"]
        days = opts["days"]
        per_day = opts["entries_per_day"]

        types = list(WorkType.objects.filter(is_active=True))
        if not types:
            self.stdout.write(self.style.WARNING("Нет WorkType. Загрузи фикстуру и попробуй снова."))
            return

        # воркеры
        workers = []
        for _ in range(workers_count):
            tg_id = random.randint(10_000_000, 99_999_999)
            w, _ = Worker.objects.get_or_create(
                telegram_id=tg_id,
                defaults=dict(
                    full_name=fake.name(),
                    username=fake.user_name(),
                    is_active=True,
                    joined_at=timezone.now(),
                ),
            )
            workers.append(w)

        # записи
        start = date.today() - timedelta(days=days - 1)
        created = 0
        for n in range(days):
            d = start + timedelta(days=n)
            for w in workers:
                # на день — до per_day разных типов
                for t in random.sample(types, k=min(per_day, len(types))):
                    qty = round(random.uniform(1, 200), 3)
                    try:
                        WorkEntry.objects.create(
                            worker=w,
                            work_type=t,
                            work_date=d,
                            quantity=qty,
                            comment=f"auto gen {qty} {t.unit}",
                        )
                        created += 1
                    except Exception:
                        # возможно упёрлись в UniqueConstraint — скипаем
                        pass

        self.stdout.write(self.style.SUCCESS(
            f"Готово: workers={len(workers)}, entries≈{created}"
        ))
