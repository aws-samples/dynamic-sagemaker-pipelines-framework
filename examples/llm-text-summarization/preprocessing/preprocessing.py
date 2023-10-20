from datasets import load_dataset
from random import randint
from transformers import AutoTokenizer

# Load dataset staged from hub in s3
preprocessing_input_local= '/opt/ml/processing/input'
# dataset = load_dataset("arrow", 
#                        data_files={
#                         'train': f'{preprocessing_input_local}/raw-prompts-train/samsum-train.arrow', 
#                         'test': f'{preprocessing_input_local}/raw-prompts-test/samsum-test.arrow'
#                         }
#                     )

#Alternatively load dataset from hugging face
dataset = load_dataset("samsum")

print(f"Train dataset size: {len(dataset['train'])}")
print(f"Test dataset size: {len(dataset['test'])}")

tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-40b")

# custom instruct prompt start
prompt_template = f"Summarize the chat dialogue:\n{{dialogue}}\n---\nSummary:\n{{summary}}{{eos_token}}"

# template dataset to add prompt to each sample
def template_dataset(sample):
    sample["text"] = prompt_template.format(dialogue=sample["dialogue"],
                                            summary=sample["summary"],
                                            eos_token=tokenizer.eos_token)
    return sample


# apply prompt template per sample
train_dataset = dataset["train"].map(template_dataset, remove_columns=list(dataset["train"].features))

print(f'Sample summarization example on base model:  {train_dataset[randint(0, len(dataset))]["text"]}')

# apply prompt template per sample
test_dataset = dataset["test"].map(template_dataset, remove_columns=list(dataset["test"].features))

 # tokenize and chunk dataset
lm_train_dataset = train_dataset.map(
    lambda sample: tokenizer(sample["text"]), batched=True, batch_size=24, remove_columns=list(train_dataset.features)
)


lm_test_dataset = test_dataset.map(
    lambda sample: tokenizer(sample["text"]), batched=True, remove_columns=list(test_dataset.features)
)

# Print total number of samples
print(f"Total number of train samples: {len(lm_train_dataset)}")

lm_train_dataset.save_to_disk(f'/opt/ml/processing/output/training')
lm_test_dataset.save_to_disk(f'/opt/ml/processing/output/testing')