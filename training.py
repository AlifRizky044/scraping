import torch
from transformers import TrainingArguments, Trainer, AutoModelForQuestionAnswering, AutoTokenizer
from datasets import Dataset, DatasetDict
import json

# Load dataset
with open("context.json", "r", encoding="utf-8") as f:
    squad_data = json.load(f)

# Convert JSON to a flat dataset format
qa_list = []
for entry in squad_data["data"]:
    for para in entry["paragraphs"]:
        context = para["context"]
        for qa in para["qas"]:
            for ans in qa["answers"]:
                qa_list.append({
                    "question": qa["question"],
                    "context": context,
                    "answers": ans  # Store the answer directly
                })

# Convert to Hugging Face Dataset format
dataset = DatasetDict({"train": Dataset.from_list(qa_list)})

# Load Pretrained Model and Tokenizer
model_name = "distilbert-base-cased-distilled-squad"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)

# ✅ Function to preprocess dataset and add start/end positions
def preprocess_function(examples):
    inputs = tokenizer(
        examples["question"],
        examples["context"],
        truncation=True,
        padding="max_length",
        max_length=384,
        return_tensors="pt"
    )
    
    # Find start and end positions of answer within context
    start_positions = []
    end_positions = []
    for i, answer in enumerate(examples["answers"]):
        start_char = answer["answer_start"]  # Start character index
        end_char = start_char + len(answer["text"])  # End character index
        
        # Convert character positions to token positions
        start_token = inputs.char_to_token(i, start_char)
        end_token = inputs.char_to_token(i, end_char - 1)

        # Handle edge cases where token conversion fails
        if start_token is None:
            start_token = tokenizer.model_max_length
        if end_token is None:
            end_token = tokenizer.model_max_length

        start_positions.append(start_token)
        end_positions.append(end_token)

    # Add to tokenized output
    inputs["start_positions"] = start_positions
    inputs["end_positions"] = end_positions
    
    return inputs

# Apply Preprocessing
tokenized_dataset = dataset.map(preprocess_function, batched=True)

# ✅ Custom Trainer Class
class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        outputs = model(**inputs)

        # Ensure 'start_positions' and 'end_positions' exist
        if "start_positions" not in inputs or "end_positions" not in inputs:
            raise ValueError("Missing 'start_positions' or 'end_positions' in training data!")

        start_loss = torch.nn.functional.cross_entropy(outputs.start_logits, inputs["start_positions"])
        end_loss = torch.nn.functional.cross_entropy(outputs.end_logits, inputs["end_positions"])
        loss = (start_loss + end_loss) / 2  # Averaging both losses
        
        return (loss, outputs) if return_outputs else loss

# Training Arguments
training_args = TrainingArguments(
    output_dir="./qa_model",
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    save_strategy="epoch",
)

# ✅ Use CustomTrainer
trainer = CustomTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["train"],
    tokenizer=tokenizer
)

# Train the model
trainer.train()

# Save the trained model
model.save_pretrained("qa_model")
tokenizer.save_pretrained("qa_model")

print("✅ Model training complete and saved!")
