import os
import torch
import transformers
from datasets import load_from_disk
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import prepare_model_for_kbit_training
from peft import LoraConfig, get_peft_model
import subprocess, shutil
import os
import nvidia

cuda_install_dir = '/'.join(nvidia.__file__.split('/')[:-1]) + '/cuda_runtime/lib/'
os.environ['LD_LIBRARY_PATH'] =  cuda_install_dir

print('*'*100)
print(torch.__version__)
print('*'*100)

# log_bucket = f"s3://{os.environ['SMP_S3BUCKETNAME']}/falcon-40b-qlora-finetune"

model_id = "tiiuae/falcon-7b"

# model_id = "tiiuae/falcon-40b"

device_map="auto"
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

# alternate config for loading unquantized model on cpu
'''
device_map = {
    "transformer.word_embeddings": 0,
    "transformer.word_embeddings_layernorm": 0,
    "lm_head": "cpu",
    "transformer.h": 0,
    "transformer.ln_f": 0,
}
bnb_config = BitsAndBytesConfig(llm_int8_enable_fp32_cpu_offload=True)
'''

lm_train_dataset= load_from_disk(dataset_path=f"/opt/ml/input/data/falcon-text-summarization-preprocess-training/")
lm_test_dataset= load_from_disk(dataset_path=f"/opt/ml/input/data/falcon-text-summarization-preprocess-testing/")

tokenizer= AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, quantization_config=bnb_config, device_map= device_map) #model prepared for LoRA training using PEFT

tokenizer.pad_token = tokenizer.eos_token


model.gradient_checkpointing_enable()
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False

config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=[
        "query_key_value",
        "dense",
        "dense_h_to_4h",
        "dense_4h_to_h",
        ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, config)

trainer = transformers.Trainer(
    model=model,
    train_dataset= lm_train_dataset,
    eval_dataset=lm_test_dataset,
    args=transformers.TrainingArguments(
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        # logging_dir=f'{log_bucket}/', # connect tensorboard for visualizing live training logs
        logging_steps=2,
        num_train_epochs=1, #num_train_epochs=1 for demonstration
        learning_rate=2e-4,
        bf16=True,
        save_strategy = "no",
        output_dir="outputs",
        report_to="tensorboard"    
    ),
    data_collator=transformers.DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

subprocess.run(["watch -n 0.5 nvidia-smi"], shell=True) #TODO: confirm output to cw logger

trainer.train()

eval_metrics= trainer.evaluate()

# throw an error if evaluation loss is above threshold. Alternatively output an evaluation.json and add the pass/fail logic as a Sagemaker pipeline step.
if eval_metrics['eval_loss'] > 2:
    raise ValueError("Evaluation loss is too high.")

# create a tarball of the model. For inference logic, untar and load appropriate .bin and .config for the llm from hugging face and serve.
trainer.save_model('/opt/ml/model')
# shutil.copytree('/opt/ml/code', os.path.join(os.environ['SM_MODEL_DIR'], 'code'))