# PawPal+ Project Reflection

## 1. System Design

Three core actions: 
    Track tasks by duration and priority
    Schedule events
    Log pet information
    
**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

    Task — Represents a single pet-care activity along with its duration, priority, and timing details.
    Pet — Represents a pet and manages the list of care tasks that belong to it.
    Owner — Represents the app user, holding their pets, daily time budget, and scheduling preferences.
    ScheduledTask — Pairs a single task with a concrete start and end time.
    Plan — Represents the generated daily schedule, tracking which tasks were included or skipped and explaining why.
    Scheduler — The engine that sorts, filters, and arranges tasks under the owner's constraints to build the final plan.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

    Yes. Times were changed from strings to integers, tracking the minutes since midnight. This is because the scheduling methods work more efficiently when they don't have to parse the string in every operation. They can now use the time as an integer directly.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

    The scheduler weighs four constraints: the owner's daily time budget, each
    task's priority, its preferred time of day, and a hard end-of-day cutoff.
    Priority matters most, tasks are sorted high-to-low so the budget is spent on what matters before anything else, and preferred times only shape when the already-chosen tasks are placed.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

    I simplified resolve_conflicts to a single sorted(tasks, key=Task.sort_key),
    trading an explicit two-pass for a shorter sort that leans on stable ordering
    and a 24*60 sentinel. Reasonable because preferred_time is always 0–1439, so
    the sentinel can never collide with a real time.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

    I used my AI assistant for help with the initial design, filling out the necessary code for each feature, and writing documentation. The most helpful prompts where when I provided a detailed multi line instruction set. Those worked quite well and got exactly what I needed done in a way that also reduced the margin for error.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

    When I wanted to update the UML diagram, it overwrote my old one. I asked it to roll back that change and create the uml_final file. This was the only major issue I had, and considering it was an error on my end. Overall the AI did a great job of suggesting exactly what I needed. I evaluated AI outputs like the class planning suggestions by checking if there was unnecessary or illogical components that weren't necessary for the purposes of this project.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

    We tested the core scheduling logic: sorting , budget filtering, conflict detection, recurrence, and plan assembly. These matter because they are the core features the owner must rely on to work correctly: right tasks chosen, sensibly ordered without double-booking, and recurring chores reliably reappearing.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

    I am mostly confident that everything in my scheduler works correctly. A couple edge cases I could test: Budget spent on a task that then gets dropped by the end of day wall, and the same Task instance shared across two pets.
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

    I am most satisfied with how everything came together cleanly and my prompts were clear enough the get the AI to do exactly what I needed.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

    I think I would spend some time on how the app looks to improve the user experience. It's pretty basic at the moment

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

    I learned that it is very important to spend plenty of time planning out your class structure before you jump in and start coding. This also helps the AI work more effectively.
