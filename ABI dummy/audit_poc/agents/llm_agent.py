import ollama


def ask_llm(prompt):

    response = ollama.chat(
        model="llama3.2:1b",
        messages=[
            {
                "role": "system",
                "content": """
                You are an IT audit reasoning assistant.

                Your job is to:
                - identify gaps
                - diagnose workpaper completeness
                - compare historical workpapers
                - recommend remediation steps
                - explain audit risks clearly
                """
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]