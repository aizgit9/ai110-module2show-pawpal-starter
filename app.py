import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler

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

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    pet.add_task(Task(title=task_title, duration_minutes=int(duration), priority=priority))

if pet.list_tasks():
    st.write("Current tasks:")
    st.table(
        [
            {
                "title": t.title,
                "duration_minutes": t.duration_minutes,
                "priority": t.priority,
                "done": "✓" if t.completed else "",
            }
            for t in pet.list_tasks()
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
                to_complete.mark_complete()
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
    plan = Scheduler(owner, start_time=int(start_hour) * 60).build_plan()

    if plan.items:
        st.write("### Today's Schedule")
        st.table(plan.to_table())
        st.write(f"**Total scheduled time:** {plan.total_minutes} min")
        with st.expander("Why this plan? (reasoning)"):
            st.text(plan.explain())
    else:
        st.warning(
            "No tasks could be scheduled. Add some tasks or increase the available time."
        )
