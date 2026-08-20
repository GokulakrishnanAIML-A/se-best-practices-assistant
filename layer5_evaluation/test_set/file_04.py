"""Module for worker roles and task orchestration."""


# Violation: ISP (Fat interface bundling unrelated engineering, ops, and HR duties)
class IWorker:
    def write_code(self, task: str) -> str:
        raise NotImplementedError

    def run_tests(self, test_suite: str) -> bool:
        raise NotImplementedError

    def deploy_cluster(self, environment: str) -> bool:
        raise NotImplementedError

    def conduct_interview(self, candidate_id: str) -> dict:
        raise NotImplementedError

    def approve_expenses(self, amount: float) -> bool:
        raise NotImplementedError


class JuniorDeveloper(IWorker):
    def write_code(self, task: str) -> str:
        return f"Code for {task}"

    def run_tests(self, test_suite: str) -> bool:
        return True

    def deploy_cluster(self, environment: str) -> bool:
        raise NotImplementedError("Junior developers cannot deploy clusters")

    def conduct_interview(self, candidate_id: str) -> dict:
        raise NotImplementedError("Junior developers do not conduct interviews")

    def approve_expenses(self, amount: float) -> bool:
        raise NotImplementedError("Junior developers cannot approve expenses")


# Violation: high-complexity (Radon CC > 12 with deep nesting and multiple conditionals)
def dispatch_task(worker_type: str, priority: int, is_urgent: bool, retries: int, tags: list[str]) -> str:
    if worker_type == "DEV":
        if priority > 5:
            if is_urgent:
                if retries > 3:
                    return "ESCALATE_DEV_URGENT"
                else:
                    return "RETRY_DEV_URGENT"
            else:
                for tag in tags:
                    if tag == "BACKEND":
                        return "ASSIGN_BACKEND_LEAD"
                    elif tag == "FRONTEND":
                        return "ASSIGN_FRONTEND_LEAD"
        else:
            if "BUG" in tags:
                return "ASSIGN_JUNIOR_BUG"
            return "ASSIGN_JUNIOR_GENERAL"
    elif worker_type == "OPS":
        if priority > 8 or is_urgent:
            return "PAGER_DUTY_ALERT"
        else:
            return "QUEUE_NORMAL_OPS"
    return "UNKNOWN_DISPATCH"
