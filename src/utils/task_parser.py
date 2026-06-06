from healthcare_ai.schemas.planner_schema import PlannerOutput, PlannedTask


def task_objectives(planner_output: PlannerOutput | None) -> list[str]:
    if planner_output is None:
        return []
    return [task.objective for task in planner_output.tasks]


def tasks_by_capability(planner_output: PlannerOutput | None, capability: str) -> list[PlannedTask]:
    if planner_output is None:
        return []
    return [task for task in planner_output.tasks if capability in task.required_capabilities]
