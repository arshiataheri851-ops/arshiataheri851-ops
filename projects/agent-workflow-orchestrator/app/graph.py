from .models import TaskSpec


class WorkflowValidationError(ValueError):
    pass


def validate_graph(tasks: list[TaskSpec]) -> None:
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise WorkflowValidationError("task_id values must be unique")
    known = set(ids)
    for task in tasks:
        unknown = set(task.depends_on) - known
        if unknown:
            raise WorkflowValidationError(
                f"task {task.task_id!r} has unknown dependencies: {sorted(unknown)}"
            )
        if task.task_id in task.depends_on:
            raise WorkflowValidationError(f"task {task.task_id!r} cannot depend on itself")

    dependencies = {task.task_id: set(task.depends_on) for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise WorkflowValidationError("workflow dependency graph contains a cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)
