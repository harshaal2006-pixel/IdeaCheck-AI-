from crewai import Task
from agents import (
    problem_agent, customer_agent, competitor_agent,
    mvp_agent, revenue_agent, pitch_agent, risk_agent
)

def create_tasks(idea):

    task1 = Task(
    description=f"""In 150 words maximum, analyse this startup idea: '{idea}'. 
    Is the problem real? Is it painful enough? Who faces this problem?
    At the end always write exactly: VALIDATION SCORE: X/10""",
    agent=problem_agent,
    expected_output="Brief problem validation with VALIDATION SCORE: X/10 at the end"
)
    
    task2 = Task(
        description=f"In 150 words maximum, for '{idea}', describe the target customer persona briefly.",
        agent=customer_agent,
        expected_output="Brief customer persona"
    )

    task3 = Task(
        description=f"In 150 words maximum, for '{idea}', list 3 main competitors and one market gap.",
        agent=competitor_agent,
        expected_output="Brief competitor list and market gap"
    )

    task4 = Task(
        description=f"In 150 words maximum, for '{idea}', list top 3 MVP features only.",
        agent=mvp_agent,
        expected_output="Top 3 MVP features"
    )

    task5 = Task(
        description=f"In 150 words maximum, for '{idea}', suggest the best revenue model and pricing.",
        agent=revenue_agent,
        expected_output="Brief revenue model"
    )

    task6 = Task(
        description=f"In 150 words maximum, write an investor pitch for '{idea}'.",
        agent=pitch_agent,
        expected_output="150 word investor pitch"
    )

    task7 = Task(
    description=f"In 150 words maximum, for '{idea}', identify top 5 risks and one mitigation strategy for each.",
    agent=risk_agent,
    expected_output="Top 5 risks with mitigation strategies"
    )

    return [task1, task2, task3, task4, task5, task6, task7]