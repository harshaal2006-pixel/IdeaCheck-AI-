from crewai import Crew, Process
from agents import (
    problem_agent, customer_agent, competitor_agent,
    mvp_agent, revenue_agent, pitch_agent
)
from tasks import create_tasks

def validate_startup(idea):
    tasks = create_tasks(idea)

    crew = Crew(
        agents=[
            problem_agent, customer_agent, competitor_agent,
            mvp_agent, revenue_agent, pitch_agent
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    return result

if __name__ == "__main__":
    print("Starting Startup Validator...")
    idea = input("Enter your startup idea: ")
    print(f"Validating: {idea}")
    result = validate_startup(idea)
    print("\n===== FINAL REPORT =====")
    print(result)