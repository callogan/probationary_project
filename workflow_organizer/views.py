from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet, Q, Count
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic


from .forms import (
    TaskForm,
    TaskTypeForm,
    TaskTypeSearchForm,
    PositionForm,
    PositionSearchForm,
    WorkerCreateForm,
    ProjectForm,
    TeamForm,
)
from .models import Tag, Task, TaskType, Position, Worker, Project, Team


def index(request):
    """View function for the home page of the site."""

    context = {
        "num_teams": Team.objects.count(),
        "num_projects": Project.objects.count(),
        "num_workers": get_user_model().objects.count()
    }

    return render(request, "workflow_organizer/index.html", context=context)


class TaskTypeListView(LoginRequiredMixin, generic.ListView):
    model = TaskType
    context_object_name = "task_type_list"
    paginate_by = 3

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(TaskTypeListView, self).get_context_data(**kwargs)
        name = self.request.GET.get("name", "")
        context["search_form"] = TaskTypeSearchForm(initial={
            "name": name
        })
        return context

    def get_queryset(self):
        queryset = TaskType.objects.all()

        form = TaskTypeSearchForm(self.request.GET)
        if form.is_valid():
            return queryset.filter(name__icontains=form.cleaned_data["name"])
        return queryset


class TaskTypeCreate(LoginRequiredMixin, generic.CreateView):
    model = TaskType
    form_class = TaskTypeForm
    success_url = reverse_lazy("workflow_organizer:task-type-list")


class TaskTypeUpdate(LoginRequiredMixin, generic.UpdateView):
    model = TaskType
    form_class = TaskTypeForm
    success_url = reverse_lazy("workflow_organizer:task-type-list")


class TaskTypeDelete(LoginRequiredMixin, generic.DeleteView):
    model = TaskType
    success_url = reverse_lazy("workflow_organizer:task-type-list")


class PositionListView(LoginRequiredMixin, generic.ListView):
    model = Position
    paginate_by = 3

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(PositionListView, self).get_context_data(**kwargs)
        name = self.request.GET.get("name", "")
        context["search_form"] = PositionSearchForm(initial={
            "name": name
        })
        return context

    def get_queryset(self) -> QuerySet:
        queryset = Position.objects.all()
        form = PositionSearchForm(self.request.GET)

        if form.is_valid():
            queryset = Position.objects.filter(
                name__icontains=form.cleaned_data["name"]
            )
        return queryset


class PositionCreate(LoginRequiredMixin, generic.CreateView):
    model = Position
    form_class = PositionForm
    success_url = reverse_lazy("workflow_organizer:position-list")


class PositionUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Position
    form_class = PositionForm
    success_url = reverse_lazy("workflow_organizer:position-list")


class PositionDelete(LoginRequiredMixin, generic.DeleteView):
    model = Position
    success_url = reverse_lazy("workflow_organizer:position-list")


class TeamDetailView(LoginRequiredMixin, generic.DetailView):
    model = Team


class WorkerDetailView(LoginRequiredMixin, generic.DetailView):
    model = Worker
    queryset = get_user_model().objects.select_related("position")

class WorkerCreate(generic.CreateView):
    model = Worker
    form_class = WorkerCreateForm
    success_url = reverse_lazy("workflow_organizer:index")


class WorkerUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Worker
    form_class = WorkerCreateForm

    def get_success_url(self):
        return reverse_lazy("workflow_organizer:worker-detail", kwargs={
            "pk": self.kwargs["pk"]
        })


class WorkerDelete(LoginRequiredMixin, generic.DeleteView):
    model = Worker
    success_url = reverse_lazy("workflow_organizer:index")


@login_required
def toggle_assign_to_task(request, pk):
    assignee = get_user_model().objects.get(id=request.user.id)
    if (
        Task.objects.get(id=pk) in assignee.tasks.all()
    ):
        assignee.tasks.remove(pk)
    else:
        assignee.tasks.add(pk)
    return HttpResponseRedirect(reverse_lazy(
        "workflow_organizer:task-detail", args=[pk]
    ))

    return render(request, "workflow_organizer/task_panel.html", context)


class TaskDetailView(LoginRequiredMixin, generic.DetailView):
    model = Task
    queryset = Task.objects.select_related(
        "task_type"
    ).prefetch_related("assignees")


class TaskCreate(LoginRequiredMixin, generic.CreateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy("workflow_organizer:task-panel")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TaskUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Task
    form_class = TaskForm

    def get_success_url(self):
        return reverse_lazy("workflow_organizer:task-detail", kwargs={
            "pk": self.kwargs["pk"]
        })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TaskDelete(LoginRequiredMixin, generic.DeleteView):
    model = Task
    success_url = reverse_lazy("workflow_organizer:index")


def dashboard(request):

    teams = Team.objects.annotate(projects_count=Count("projects"))

    context = {
        "projects": Project.objects.select_related("team"),
        "teams": teams
    }

    return render(request, "workflow_organizer/dashboard.html", context)


def task_panel(request):
    tag = request.GET.get("tag") or ""
    tags = Tag.objects.filter(name__contains=tag) if tag else Tag.objects.all()
    queue_tasks = Task.objects.filter(status='QUEUE', tags__name__contains=tag).distinct()
    underway_tasks = Task.objects.filter(status='UNDERWAY', tags__name__contains=tag).distinct()
    completed_tasks = Task.objects.filter(status='COMPLETED', tags__name__contains=tag).distinct()
    context = {
        'queue_tasks': queue_tasks,
        'underway_tasks': underway_tasks,
        'completed_tasks': completed_tasks,
        'tags': tags,
    }
    return render(request, 'workflow_organizer/task_panel.html', context)


def project_tracking_panel(request):
    total_projects = Project.objects.all()
    completed_projects = Project.objects.filter(is_completed=True).count()
    projects = Project.objects.all()

    progress_list = []
    for project in projects:
        if project.is_completed:
            progress_list.append(100)
        elif project.progress is not None:
            progress_list.append(project.progress)
        else:
            progress_list.append(0)

    time_constraints = Project.objects.values_list('time_constraints', flat=True)
    funds = Project.objects.values_list('budget', flat=True)

    context = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'progress': progress_list,
        'time_constraints': time_constraints,
        'funds': funds,
    }

    return render(request, 'workflow_organizer/project_tracking_panel.html', context)


class UsersListView(generic.ListView):
    model = Worker
    context_object_name = 'users'
    ordering = ['-rating_point']
    paginate_by = 10  # If you want pagination, set the number of items per page here

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        top_users = context['object_list'][:3]
        other_users = context['object_list'][3:]
        context['top_users'] = top_users
        context['other_users'] = other_users
        return context


class ProjectDetailView(generic.DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["completed_projects"] = Project.objects.filter(is_completed=True).count()
        return context


class ProjectCreate(LoginRequiredMixin, generic.CreateView):
    model = Project
    form_class = ProjectForm
    success_url = reverse_lazy("workflow_organizer:dashboard")


class ProjectUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Project
    form_class = ProjectForm

    def get_success_url(self):
        return reverse_lazy("workflow_organizer:project-detail", kwargs={
            "pk": self.kwargs["pk"]
        })


class ProjectDelete(LoginRequiredMixin, generic.DeleteView):
    model = Project
    success_url = reverse_lazy("workflow_organizer:dashboard")


@login_required
def toggle_assign_to_project(request, pk):
    team = Team.objects.get(id=request.user.team.id)
    project = Project.objects.get(id=pk)
    if (
        project in team.projects.all()
    ):
        team.projects.remove(project)
    else:
        team.projects.add(project)
    return HttpResponseRedirect(reverse_lazy(
        "workflow_organizer:project-detail", args=[pk]
    ))


class TeamCreate(LoginRequiredMixin, generic.CreateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy("workflow_organizer:dashboard")


class TeamUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy("workflow_organizer:dashboard")


class TeamDelete(LoginRequiredMixin, generic.DeleteView):
    model = Team
    success_url = reverse_lazy("workflow_organizer:dashboard")

    class Meta:
        fields = "__all__"


@login_required
def toggle_add_to_team(request, pk):
    user = get_user_model().objects.get(id=pk)
    team = Team.objects.get(id=request.user.team.id)
    if (
        user in team.workers.all()
    ):
        team.workers.remove(user)
    else:
        team.workers.add(user)
    return HttpResponseRedirect(reverse_lazy(
        "workflow_organizer:worker-detail", args=[pk]
    ))
