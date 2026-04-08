"""Autonomous TB compound loop — runs headless tasks on schedule."""

import asyncio
import json
import logging
import subprocess
from datetime import date
from pathlib import Path

logger = logging.getLogger("NucleusJobs.tb_compound")


async def run_tb_compound() -> dict:
    """Run compound loop: pick tasks -> headless Claude -> training capture."""
    try:
        brain = Path.home() / "ai-mvp-backend" / ".brain"
        config_path = brain / "driver" / "config.json"

        config = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        if not config.get("headless_enabled", False):
            return {"ok": True, "skipped": "headless_enabled is false"}

        # Daily task budget
        daily_cap = config.get("autonomous_daily_task_cap", 5)
        budget_path = brain / "driver" / "daily_budget.json"
        today = date.today().isoformat()
        budget = {}
        if budget_path.exists():
            try:
                budget = json.loads(budget_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        if budget.get("date") != today:
            budget = {"date": today, "tasks_run": 0}
        if budget["tasks_run"] >= daily_cap:
            logger.info("Daily cap reached (%d/%d)", budget["tasks_run"], daily_cap)
            return {"ok": True, "skipped": f"daily cap {daily_cap}"}

        remaining = daily_cap - budget["tasks_run"]
        branch = config.get("autonomous_branch", "tb/autonomous")
        driver = Path.home() / "ai-mvp-backend" / "scripts" / "third_brother_driver.py"

        if not driver.exists():
            return {"ok": False, "error": f"driver not found: {driver}"}

        result = await asyncio.to_thread(
            subprocess.run,
            ["python3", str(driver), "--compound", str(remaining),
             "--branch", branch],
            capture_output=True, text=True,
            timeout=7200,
        )

        # Update budget
        tasks_done = result.stdout.count("Task completed") if result.stdout else 0
        budget["tasks_run"] = budget.get("tasks_run", 0) + max(tasks_done, 1)
        budget_path.parent.mkdir(parents=True, exist_ok=True)
        budget_path.write_text(json.dumps(budget))

        logger.info("TB compound: %d tasks, exit=%d", tasks_done, result.returncode)
        return {"ok": result.returncode == 0, "tasks": tasks_done}
    except subprocess.TimeoutExpired:
        logger.warning("TB compound timed out (2h)")
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        logger.error("TB compound failed: %s", e)
        return {"ok": False, "error": str(e)}
