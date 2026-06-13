"""
Load test — 100 concurrent users.
Run with: locust -f load_test.py --users 100 --spawn-rate 10 --host https://yourdomain.com

Pass criteria (from spec):
  P50 latency < 200ms  for rule-based endpoints
  P95 latency < 15s    for LLM endpoints
  Zero 5xx errors
  Memory < 40 GB RAM
"""
import time
from locust import HttpUser, task, between


class StudyAIUser(HttpUser):
    wait_time = between(2, 8)

    def on_start(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"email": f"test{self.user_id}@test.com", "password": "testpass"},
        )
        if resp.status_code != 200:
            self.environment.runner.quit()

    @task(5)
    def view_universities(self):
        self.client.get("/api/universities?country=UK")

    @task(3)
    def get_profile_score(self):
        self.client.get("/api/profile/score")

    @task(2)
    def check_documents(self):
        self.client.get("/api/documents/checklist")

    @task(1)
    def generate_sop(self):
        resp = self.client.post(
            "/api/sop/generate",
            json={"university_id": "00000000-0000-0000-0000-000000000001"},
        )
        if resp.status_code == 200:
            task_id = resp.json().get("task_id")
            if task_id:
                for _ in range(30):
                    result = self.client.get(f"/api/sop/tasks/{task_id}")
                    if result.json().get("status") == "complete":
                        break
                    time.sleep(2)
