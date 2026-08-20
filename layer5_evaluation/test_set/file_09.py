"""Module for omnichannel notification dispatching."""

import time


# Violation: ISP (Fat interface bundling disparate delivery channels)
class INotificationHandler:
    def send_email(self, to: str, subject: str, body: str) -> bool:
        raise NotImplementedError

    def send_sms(self, phone_number: str, message: str) -> bool:
        raise NotImplementedError

    def send_push_notification(self, device_token: str, payload: dict) -> bool:
        raise NotImplementedError

    def send_pager_alert(self, team_id: str, urgency: str) -> bool:
        raise NotImplementedError


class SimpleEmailNotifier(INotificationHandler):
    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to}: {subject}")
        return True

    def send_sms(self, phone_number: str, message: str) -> bool:
        raise NotImplementedError("SMS not supported by SimpleEmailNotifier")

    def send_push_notification(self, device_token: str, payload: dict) -> bool:
        raise NotImplementedError("Push notifications not supported by SimpleEmailNotifier")

    def send_pager_alert(self, team_id: str, urgency: str) -> bool:
        raise NotImplementedError("Pager alerts not supported by SimpleEmailNotifier")


# Violation: long-function (> 50 lines handling template parsing, throttling, dispatching, and auditing)
def dispatch_batch_notifications(recipients: list[dict], template: str, max_per_second: int) -> dict:
    successful = []
    failed = []
    throttle_interval = 1.0 / max_per_second if max_per_second > 0 else 0.0

    for item in recipients:
        email = item.get("email")
        user_name = item.get("name", "Valued Customer")
        account_status = item.get("status", "ACTIVE")

        if not email or "@" not in email:
            failed.append({"recipient": email, "reason": "Invalid email address"})
            continue

        if account_status == "SUSPENDED":
            failed.append({"recipient": email, "reason": "Account is suspended"})
            continue

        personalized_body = template.replace("{{name}}", user_name)
        personalized_body = personalized_body.replace("{{date}}", time.strftime("%Y-%m-%d"))

        try:
            # Simulate dispatch
            time.sleep(throttle_interval)
            successful.append({
                "email": email,
                "timestamp": time.time(),
                "body_length": len(personalized_body),
            })
        except Exception as exc:
            failed.append({"recipient": email, "reason": str(exc)})

    audit_summary = {
        "total_requested": len(recipients),
        "total_sent": len(successful),
        "total_failed": len(failed),
        "success_rate": (len(successful) / len(recipients) * 100) if recipients else 0.0,
    }

    return {"summary": audit_summary, "failed": failed}
