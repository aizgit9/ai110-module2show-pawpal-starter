"""Temporary testing ground for PawPal+.

Run with:  python main.py

Builds a small owner/pet/task setup by hand and prints the generated daily
schedule to the terminal, so we can eyeball the scheduling logic without the
Streamlit UI.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def hhmm(hour: int, minute: int = 0) -> int:
    """Small helper: convert a clock time to minutes-since-midnight."""
    return hour * 60 + minute


def main() -> None:
    # --- Owner with a day's time budget ---------------------------------
    owner = Owner(name="Jordan", available_minutes=120)

    # --- Two pets -------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    biscuit = Pet(name="Biscuit", species="cat", age=5)

    # --- At least three tasks, with different preferred times -----------
    mochi.add_task(Task("Morning walk", 30, "high", preferred_time=hhmm(8)))
    mochi.add_task(Task("Feeding", 10, "high", preferred_time=hhmm(9)))
    mochi.add_task(Task("Fetch / play", 20, "medium", preferred_time=hhmm(17)))

    biscuit.add_task(Task("Feeding", 10, "high", preferred_time=hhmm(9, 30)))
    biscuit.add_task(Task("Litter box", 5, "medium"))
    biscuit.add_task(Task("Grooming", 25, "low", preferred_time=hhmm(19)))

    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # --- Generate the plan ----------------------------------------------
    scheduler = Scheduler(owner, start_time=hhmm(8))
    plan = scheduler.build_plan()

    # --- Print "Today's Schedule" ---------------------------------------
    print("=" * 44)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 44)
    print(plan.explain())
    print("=" * 44)


if __name__ == "__main__":
    main()
