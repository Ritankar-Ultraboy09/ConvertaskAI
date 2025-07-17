import requests
import re
from datetime import datetime, timedelta
import time

NOTION_TOKEN = "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"
DATABASE_ID = "222ed913d3ae80adac53e5e30b16bda7"

REQUEST_DELAY = 0.3

def est_deadline(task_text):
    task_lower = task_text.lower()
    match = re.search(
        r'\b(by|before|on)\s+(tomorrow|\d{1,2}(?:st|nd|rd|th)?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
        task_lower
    )

    if "tomorrow" in task_lower:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif match:
        date_part = match.group(2)
        if '/' in date_part:
            month, day = date_part.split('/')[:2]
            current_year = datetime.now().year
            return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
        return (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    return None

def push_to_notion(summary_dict, speaker="Unknown"):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    def upload(task, item_type, deadline=None):
        if not task.strip():
            return False

        properties = {
            "Name": {"title": [{"text": {"content": task}}]},
            "Type": {"select": {"name": item_type}},
            "Status": {"status": {"name": "Not started"}},
            "Speaker": {"rich_text": [{"text": {"content": speaker}}]},
            "From": {"rich_text": [{"text": {"content": "Summary"}}]},
        }
        if deadline:
            properties["Deadline"] = {"date": {"start": deadline}}

        payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": properties
        }

        try:
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=10)
            res.raise_for_status()
            return True
        except Exception as e:
            print(f"[❌] Failed to upload to Notion: {e}")
            return False

    counts = {"actions": 0, "decisions": 0, "followups": 0, "errors": 0}

    for task in summary_dict.get("actions", []):
        deadline = est_deadline(task)
        if upload(task, "Action", deadline):
            counts["actions"] += 1
        else:
            counts["errors"] += 1
        time.sleep(REQUEST_DELAY)

    for task in summary_dict.get("decisions", []):
        if upload(task, "Decision"):
            counts["decisions"] += 1
        else:
            counts["errors"] += 1
        time.sleep(REQUEST_DELAY)

    for task in summary_dict.get("followups", []):
        deadline = est_deadline(task)
        if upload(task, "Follow-up", deadline):
            counts["followups"] += 1
        else:
            counts["errors"] += 1
        time.sleep(REQUEST_DELAY)

    print("[✅] Final push summary to Notion:", counts)
    return counts
