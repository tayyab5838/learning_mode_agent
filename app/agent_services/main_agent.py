from agents import Agent

triage_agent = Agent(name="Assistant", instructions="You are a helpful assistant")


thread_title_generator_Agent = Agent(
                    name="Generate Thread Title",
                    instructions="""You are a helpful assistant that generates short, descriptive titles "
                    "for conversation threads. Generate a title that is 3-6 words maximum, "
                    "capturing the main topic or intent of the message. don't give title name as question instead summarize"
                    "Respond with ONLY the title, nothing else.
                    Examples:
                    User: "What’s the difference between list and tuple in Python?"
                    Title: "List vs Tuple in Python"

                    User: "Explain how to use Alembic in FastAPI"
                    Title: "Using Alembic with FastAPI"
                    """
                )