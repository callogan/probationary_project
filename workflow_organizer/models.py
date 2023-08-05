import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import QuerySet, Q


class TaskType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    depiction = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=255, unique=True)
    duties = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name

    def duties_to_a_list(self) -> list:
        return list(self.duties.split(";"))[:-1]


class Team(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name

    def sum_of_budget(self) -> int:
        return sum(project.budget for project in self.projects.all())


class Worker(AbstractUser):
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="workers",
        blank=True,
        null=True
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="workers",
        null=True,
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="worker_permissions"
    )

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="worker_groups"
    )
    rating_point = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.username} ({self.first_name} {self.last_name})"

    def finished_tasks(self) -> QuerySet:
        return self.tasks.filter(is_completed=True)

    def underway_tasks(self) -> QuerySet:
        return self.tasks.filter(
            Q(time_constraints__gt=datetime.date.today()) & Q(is_completed=False))

    def past_due_tasks(self) -> QuerySet:
        return self.tasks.filter(
            Q(time_constraints__lt=datetime.date.today()), Q(is_completed=False)
        )


class Project(models.Model):
    name = models.CharField(max_length=255)
    depiction = models.TextField()
    is_completed = models.BooleanField()
    time_constraints = models.DateField()
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="projects"
    )
    budget = models.DecimalField(decimal_places=2, max_digits=8, default=0)
    progress = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Task(models.Model):

    PRIORITY_CHOICES = [
        ("U", "Urgent"),
        ("A", "Average"),
        ("S", "Side-tracked")
    ]

    STATUS_CHOICES = [
        ('QUEUE', 'Queue'),
        ('UNDERWAY', 'Underway'),
        ('COMPLETED', 'Completed'),
    ]

    name = models.CharField(max_length=255)
    depiction = models.TextField()
    time_constraints = models.DateField()
    is_completed = models.BooleanField()
    priority = models.CharField(
        max_length=1,
        choices=PRIORITY_CHOICES,
        default="S"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='QUEUE',
        )

    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="tasks",
        blank=True
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="task_permissions"
    )

    tags = models.ManyToManyField(Tag)

    def tags_remained(self) -> int:
        count = self.tags.count() - 1
        return count if count > 0 else 0

    def __str__(self) -> str:
        return f"{self.name} (priority: {self.priority})"

