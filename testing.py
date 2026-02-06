import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

# Load the trained model and tokenizer
model_path = "qa_model"
model = AutoModelForQuestionAnswering.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# Function to generate more human-like answers
def answer_question(question, context):
    inputs = tokenizer(question, context, return_tensors="pt", truncation=True, padding=True, max_length=384)
    with torch.no_grad():
        outputs = model(**inputs)

    start_logits = outputs.start_logits
    end_logits = outputs.end_logits

    start_index = torch.argmax(start_logits)
    end_index = torch.argmax(end_logits) + 1

    answer = tokenizer.convert_tokens_to_string(
        tokenizer.convert_ids_to_tokens(inputs["input_ids"][0][start_index:end_index])
    ).strip()

    # Define response templates for more natural answers
    response_templates = {
        "who won": "The champion of H3RO Esports 5.0 was {}! They played exceptionally well throughout the tournament.",
        "second place": "{} secured second place in the competition after an intense battle in the finals.",
        "prize pool": "The total prize pool for the tournament was {}. A significant amount for an esports event!",
        "when": "{} was the scheduled date for this exciting esports tournament.",
        "where": "Fans could watch the tournament live on {} and enjoy the thrilling matches.",
        "teams": "A total of {} teams competed in the event, making it a highly competitive tournament."
    }

    # Apply template-based responses
    for key, template in response_templates.items():
        if key in question.lower():
            return template.format(answer)

    # Default response if no specific template applies
    return f"Based on the information available, the answer is: {answer}."

# Tournament context
context = """
The H3RO Esports 5.0 was an online Mobile Legends: Bang Bang tournament held from May 13 to May 26, 2024, in Indonesia.
Organized by H3RO and sponsored by Tri Indonesia, the event featured 16 teams competing for a prize pool of Rp300,000,000 IDR.
Fnatic ONIC won the championship, EVOS Holy finished second, and Alter Ego finished third.
The final match was a Best-of-Seven format held on May 26, 2024.
The event had a peak viewership of 166,231 and was streamed on YouTube and Facebook.
"""

# Interactive testing
print("H3RO Esports 5.0 - Ask Me Anything!")
print("Type 'exit' to quit.\n")

while True:
    question = input("Enter your question: ")
    if question.lower() == "exit":
        break
    
    result = answer_question(question, context)
    print(f"Answer: {result}\n")
