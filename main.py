"""Temporary testing ground for PawPal+.

Run with:  python main.py

Builds a small owner/pet/task setup by hand and prints the generated daily
schedule to the terminal, so we can eyeball the scheduling logic without the
Streamlit UI. Tasks are added deliberately out of chronological order so we can
see Task.sort_key put them back in order, and Owner.find_tasks slice them.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def hhmm(hour: int, minute: int = 0) -> int:
    """Small helper: convert a clock time to minutes-since-midnight."""
    return hour * 60 + minute


def format_time(minutes: int) -> str:
    """Render minutes-since-midnight as HH:MM, or '(no time)' for untimed tasks."""
    if minutes >= 24 * 60:
        return "(no time)"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def main() -> None:
    # --- Owner with a day's time budget ---------------------------------
    owner = Owner(name="Jordan", available_minutes=120)

    # --- Two pets -------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    biscuit = Pet(name="Biscuit", species="cat", age=5)

    # --- Tasks added OUT OF ORDER on purpose ----------------------------
    # Evening play goes in before the morning walk; an untimed litter-box
    # task is sprinkled in the middle. Sorting/filtering should tidy this up.
    mochi.add_task(Task("Fetch / play", 20, "medium", preferred_time=hhmm(17)))
    biscuit.add_task(Task("Grooming", 25, "low", preferred_time=hhmm(19), recurrence="weekly"))
    mochi.add_task(Task("Morning walk", 30, "high", preferred_time=hhmm(8), recurrence="daily"))
    biscuit.add_task(Task("Litter box", 5, "medium"))  # no preferred_time
    biscuit.add_task(Task("Feeding", 10, "high", preferred_time=hhmm(9, 30), recurrence="daily"))
    mochi.add_task(Task("Feeding", 10, "high", preferred_time=hhmm(9), recurrence="daily"))

    # Two tasks deliberately requesting the SAME 08:00 slot -> a conflict.
    # Mochi's Morning walk (08:00) already occupies that window; the vet call
    # for Biscuit collides with it across different pets.
    biscuit.add_task(Task("Vet call", 20, "high", preferred_time=hhmm(8)))

    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # Mark one task done so the completion filter has something to hide.
    owner.find_tasks(pet_name="Biscuit", completed=False)[0].mark_complete()

    # --- Sorting: all tasks by preferred time (Task.sort_key) -----------
    print("=" * 52)
    print("All tasks, sorted chronologically by preferred time")
    print("=" * 52)
    for task in sorted(owner.find_tasks(), key=Task.sort_key):
        print(f"  {format_time(task.sort_key()):>9}  {task.summary()}")

    # --- Filtering: by pet name (Owner.find_tasks) ----------------------
    print("\n" + "=" * 52)
    print("Filter: only Mochi's tasks (sorted by time)")
    print("=" * 52)
    for task in sorted(owner.find_tasks(pet_name="Mochi"), key=Task.sort_key):
        print(f"  {format_time(task.sort_key()):>9}  {task.summary()}")

    # --- Filtering: by completion status --------------------------------
    print("\n" + "=" * 52)
    print("Filter: open vs. completed tasks")
    print("=" * 52)
    open_tasks = owner.find_tasks(completed=False)
    done_tasks = owner.find_tasks(completed=True)
    print(f"  Open ({len(open_tasks)}):")
    for task in open_tasks:
        print(f"    - {task.summary()}")
    print(f"  Completed ({len(done_tasks)}):")
    for task in done_tasks:
        print(f"    - {task.summary()}")

    # --- Recurrence: completing a daily task spawns the next one --------
    print("\n" + "=" * 52)
    print("Recurrence: complete Mochi's daily walk")
    print("=" * 52)
    walk = next(t for t in owner.find_tasks(pet_name="Mochi") if t.title == "Morning walk")
    before = len(owner.find_tasks(pet_name="Mochi", completed=False))
    next_walk = walk.mark_complete()
    if next_walk is not None:
        mochi.add_task(next_walk)
    after = len(owner.find_tasks(pet_name="Mochi", completed=False))
    print(f"  Marked '{walk.title}' done (recurrence={walk.recurrence}).")
    print(f"  Spawned next occurrence: open={next_walk is not None and not next_walk.completed}, "
          f"same time={format_time(next_walk.sort_key()) if next_walk else 'n/a'}")
    print(f"  Mochi's open task count: {before} -> {after} (unchanged: one done, one fresh)")

    # --- Conflict detection ---------------------------------------------
    scheduler = Scheduler(owner, start_time=hhmm(8))
    print("\n" + "=" * 52)
    print("Conflict detection")
    print("=" * 52)
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  [!] {warning}")
    else:
        print("  No conflicts detected.")

    # --- Generate the plan ----------------------------------------------
    plan = scheduler.build_plan()

    # --- Print "Today's Schedule" ---------------------------------------
    print("\n" + "=" * 52)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 52)
    print(plan.explain())
    print("=" * 52)


if __name__ == "__main__":
    main()
