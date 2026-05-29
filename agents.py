from crewai import Agent, LLM
from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

openrouter_key = os.getenv("NVIDIA_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
print("DEBUG KEY:", openrouter_key)

if not openrouter_key:
    raise ValueError("NVIDIA_API_KEY not found. Please set it in .env or Streamlit secrets.")

llm = LLM(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    api_key=nvidia_api_key,
    base_url="https://integrate.api.nvidia.com/v1",
    max_tokens=500   # ✅ safe limit
)

problem_agent = Agent(
    role="Problem Analyst",
    goal="Validate whether the startup idea solves a real and painful problem",
    backstory="You are an experienced entrepreneur who critically evaluates if a problem is real and worth solving.",
    llm=llm,
    verbose=True
)

customer_agent = Agent(
    role="Customer Research Specialist",
    goal="Build a detailed customer persona for the startup idea",
    backstory="You are a UX researcher who identifies exactly who the customer is and their pain points.",
    llm=llm,
    verbose=True
)

competitor_agent = Agent(
    role="Competitor Analyst",
    goal="Identify competitors and find market gaps",
    backstory="You are a market research expert who maps competitors and finds gaps to exploit.",
    llm=llm,
    verbose=True
)

mvp_agent = Agent(
    role="Product Manager",
    goal="Define the Minimum Viable Product feature list",
    backstory="You are a product manager who knows exactly which features to build first.",
    llm=llm,
    verbose=True
)

revenue_agent = Agent(
    role="Revenue Strategist",
    goal="Design a monetization plan for the startup",
    backstory="You are a business model expert who identifies the best revenue streams.",
    llm=llm,
    verbose=True
)

pitch_agent = Agent(
    role="Startup Pitch Writer",
    goal="Write a compelling investor-ready pitch summary",
    backstory="You are a pitch consultant who synthesizes research into a powerful investor pitch.",
    llm=llm,
    verbose=True
)

risk_agent = Agent(
    role="Risk Analyst",
    goal="Identify top risks and mitigation strategies for the startup",
    backstory="You are a startup risk expert who identifies the top 5 risks and practical solutions for early-stage startups.",
    llm=llm,
    verbose=True
)
