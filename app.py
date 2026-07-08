import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler, format_time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

# Create the Owner + Pet once and keep them in the session "vault" so tasks
# added on earlier reruns aren't lost. On later reruns the key already exists,
# so we reuse the same objects instead of building empty ones.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
    st.session_state.owner.add_pet(Pet(name=pet_name, species=species))

owner = st.session_state.owner
pet = owner.pets[0]

# Keep the persisted objects in sync with the input fields on each rerun.
owner.name = owner_name
pet.name = pet_name
pet.species = species

st.markdown("### Tasks")
st.caption("Add care tasks for your pet. These feed directly into the scheduler.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    pref_hour = st.number_input(
        "Preferred hour",
        min_value=-1,
        max_value=23,
        value=-1,
        help="Hour of day to start this task (0–23). Leave at -1 for no preference.",
    )

if st.button("Add task"):
    preferred_time = None if pref_hour < 0 else int(pref_hour) * 60
    pet.add_task(
        Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority,
            preferred_time=preferred_time,
        )
    )

if pet.list_tasks():
    st.write("**Current tasks** (sorted chronologically by preferred time):")
    # Sort for display using the same key the scheduler uses (untimed tasks last).
    st.table(
        [
            {
                "when": format_time(t.preferred_time) if t.preferred_time is not None else "any",
                "title": t.title,
                "duration_minutes": t.duration_minutes,
                "priority": t.priority,
                "done": "✓" if t.completed else "",
            }
            for t in sorted(pet.list_tasks(), key=Task.sort_key)
        ]
    )

    # Mark a task complete so it drops out of scheduling without being deleted.
    open_tasks = [t for t in pet.list_tasks() if not t.completed]
    if open_tasks:
        done_col1, done_col2 = st.columns([3, 1])
        with done_col1:
            to_complete = st.selectbox(
                "Mark a task complete",
                open_tasks,
                format_func=lambda t: t.title,
            )
        with done_col2:
            st.write("")  # spacer to align the button with the selectbox
            if st.button("Mark done"):
                # For a recurring task, mark_complete() hands back the next
                # occurrence; add it so the chore reappears for next time.
                next_task = to_complete.mark_complete()
                if next_task is not None:
                    pet.add_task(next_task)
                st.rerun()
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Set the day's constraints, then let the Scheduler build a plan.")

sched_col1, sched_col2 = st.columns(2)
with sched_col1:
    available_minutes = st.number_input(
        "Time available today (minutes)", min_value=0, max_value=1440, value=120
    )
with sched_col2:
    start_hour = st.number_input("Start the day at (hour)", min_value=0, max_value=23, value=8)

if st.button("Generate schedule"):
    owner.available_minutes = int(available_minutes)
    scheduler = Scheduler(owner, start_time=int(start_hour) * 60)

    # Ask the scheduler about requested-time overlaps *before* building, so we
    # can surface them as warnings even though build_plan resolves them anyway.
    conflicts = scheduler.detect_conflicts()
    plan = scheduler.build_plan()

    # 1) Conflict warnings from Scheduler.detect_conflicts()
    if conflicts:
        st.warning(
            f"**⚠️ {len(conflicts)} requested-time conflict(s) detected**\n\n"
            + "\n".join(f"- {w}" for w in conflicts)
        )

    # 2) The plan itself
    if plan.items:
        st.success(
            f"✅ Scheduled {len(plan.included)} task(s) — "
            f"{plan.total_minutes} min of {owner.available_minutes} min available."
        )

        st.markdown("### 📅 Today's Schedule")
        st.table(plan.to_table())

        # Tasks that couldn't start at their requested time.
        bumped = [item.task.title for item in plan.items if item.bumped]
        if bumped:
            st.info(
                "🔀 Moved from preferred time (slot already taken): "
                + ", ".join(bumped)
            )

        # 3) Filtered-out tasks: didn't fit the budget or ran past day's end.
        if plan.skipped:
            st.warning(
                f"⏭️ {len(plan.skipped)} task(s) skipped — didn't fit the time "
                "budget or ran past the end of the day:"
            )
            st.table(
                [
                    {
                        "title": t.title,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority,
                    }
                    for t in plan.skipped
                ]
            )

        with st.expander("Why this plan? (full reasoning)"):
            st.text(plan.explain())
    else:
        st.error(
            "❌ No tasks could be scheduled. Add some open tasks or increase the "
            "available time."
        )
