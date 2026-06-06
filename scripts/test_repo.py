import asyncio
from services import scheduled_repo

async def main():
    await scheduled_repo.ensure_schema()
    print("OK: schema ensured")
    task_id = await scheduled_repo.create(
        audience="all",
        text="test",
        parse_mode="HTML",
        keyboard_json="[]",
        scheduled_at_utc="2025-01-01T00:00:00+00:00",
        tz="Europe/Moscow",
        created_by=1
    )
    print("Inserted id:", task_id)
    items = await scheduled_repo.list_upcoming()
    print("Upcoming:", items[:1])
    await scheduled_repo.cancel(task_id)
    print("Cancelled:", task_id)

if __name__ == "__main__":
    asyncio.run(main())
