#!/usr/bin/env python
# coding: utf-8

# 使用 Unsloth 框架对 Qwen2.5-7B 模型进行微调的示例代码

# In[1]:


# 导入必要的库
from unsloth import FastLanguageModel
import torch

# 设置模型参数
max_seq_length = 2048  # 设置最大序列长度，支持 RoPE 缩放
dtype = None  # 数据类型，None 表示自动检测。Tesla T4 使用 Float16，Ampere+ 使用 Bfloat16
load_in_4bit = True  # 使用 4bit 量化来减少内存使用

# 加载预训练模型和分词器
model, tokenizer = FastLanguageModel.from_pretrained(
    #model_name = "unsloth/Qwen2.5-7B",  # 使用Qwen2.5-7B模型
    model_name = "/root/autodl-tmp/models/Qwen/Qwen2___5-7B-Instruct",  # 使用Qwen2.5-7B模型
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)


# In[ ]:


# 添加LoRA适配器，只需要更新1-10%的参数
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,  # LoRA秩，建议使用8、16、32、64、128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],  # 需要应用LoRA的模块
    lora_alpha = 16,  # LoRA缩放因子
    lora_dropout = 0,  # LoRA dropout率，0为优化设置
    bias = "none",    # 偏置项设置，none为优化设置
    use_gradient_checkpointing = "unsloth",  # 使用unsloth的梯度检查点，可减少30%显存使用
    random_state = 3407,  # 随机种子
    use_rslora = False,  # 是否使用rank stabilized LoRA
    loftq_config = None,  # LoftQ配置
)


# ### 数据准备

# In[ ]:


# 定义Alpaca格式的提示模板
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

# 获取结束标记
EOS_TOKEN = tokenizer.eos_token

# 定义数据格式化函数
def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        # 必须添加EOS_TOKEN，否则生成会无限继续
        text = alpaca_prompt.format(instruction, input, output) + EOS_TOKEN
        texts.append(text)
    return { "text" : texts, }

# 加载Alpaca数据集
from datasets import load_dataset
dataset = load_dataset("/root/datasets/yahma/alpaca-cleaned", split = "train")
dataset = dataset.map(formatting_prompts_func, batched = True,)


# ### 模型训练

# In[ ]:


# 设置训练参数和训练器
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported

# 定义训练参数
training_args = TrainingArguments(
        per_device_train_batch_size = 2,  # 每个设备的训练批次大小
        gradient_accumulation_steps = 4,  # 梯度累积步数
        warmup_steps = 5,  # 预热步数
        max_steps = 60,  # 最大训练步数
        learning_rate = 2e-4,  # 学习率
        fp16 = not is_bfloat16_supported(),  # 是否使用FP16
        bf16 = is_bfloat16_supported(),  # 是否使用BF16
        logging_steps = 1,  # 日志记录步数
        optim = "adamw_8bit",  # 优化器
        weight_decay = 0.01,  # 权重衰减
        lr_scheduler_type = "linear",  # 学习率调度器类型
        seed = 3407,  # 随机种子
        output_dir = "outputs",  # 输出目录
        report_to = "none",  # 报告方式
    )

# 创建SFTTrainer实例
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False,  # 对于短序列可以设置为True，训练速度提升5倍
    args = training_args,
)


# In[ ]:


# 显示当前GPU内存状态
gpu_stats = torch.cuda.get_device_properties(0)
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")


# In[ ]:


# 开始训练
trainer_stats = trainer.train()


# In[ ]:


# 显示训练后的内存和时间统计
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
used_percentage = round(used_memory / max_memory * 100, 3)
lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
print(f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training.")
print(f"Peak reserved memory = {used_memory} GB.")
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
print(f"Peak reserved memory % of max memory = {used_percentage} %.")
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")


# ### 模型推理

# In[6]:


# 模型推理部分
FastLanguageModel.for_inference(model)  # 启用原生2倍速推理
inputs = tokenizer(
[
    alpaca_prompt.format(
        "Continue the fibonnaci sequence.",  # 指令
        "1, 1, 2, 3, 5, 8",  # 输入
        "",  # 输出留空用于生成
    )
], return_tensors = "pt").to("cuda")

# 生成输出
outputs = model.generate(**inputs, max_new_tokens = 64, use_cache = True)
tokenizer.batch_decode(outputs)


# In[10]:


# 使用TextStreamer进行连续推理
FastLanguageModel.for_inference(model)
inputs = tokenizer(
[
    alpaca_prompt.format(
        "Continue the fibonnaci sequence.",  # 指令
        "1, 1, 2, 3, 5, 8",  # 输入
        "",  # 输出留空用于生成
    )
], return_tensors = "pt").to("cuda")

from transformers import TextStreamer
text_streamer = TextStreamer(tokenizer)
_ = model.generate(**inputs, streamer = text_streamer, max_new_tokens = 128)


# ### 微调模型保存

# In[13]:


# 保存模型
model.save_pretrained("lora_model")  # 本地保存
tokenizer.save_pretrained("lora_model")


# In[14]:


# 加载保存的模型进行推理
if False:
    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "lora_model",  # 训练时使用的模型
        max_seq_length = max_seq_length,
        dtype = dtype,
        load_in_4bit = load_in_4bit,
    )
    FastLanguageModel.for_inference(model)  # 启用原生2倍速推理

# 使用保存的模型进行推理示例
inputs = tokenizer(
[
    alpaca_prompt.format(
        "What is a famous tall tower in Paris?",  # 指令
        "",  # 输入
        "",  # 输出留空用于生成
    )
], return_tensors = "pt").to("cuda")

from transformers import TextStreamer
text_streamer = TextStreamer(tokenizer)
_ = model.generate(**inputs, streamer = text_streamer, max_new_tokens = 128)


# In[15]:


# 使用Hugging Face的AutoModelForPeftCausalLM加载模型（不推荐，因为速度较慢）
if False:
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer
    model = AutoPeftModelForCausalLM.from_pretrained(
        "lora_model",  # 训练时使用的模型
        load_in_4bit = load_in_4bit,
    )
    tokenizer = AutoTokenizer.from_pretrained("lora_model")


# ### Saving to float16 for VLLM
# 
# We also support saving to `float16` directly. Select `merged_16bit` for float16 or `merged_4bit` for int4. We also allow `lora` adapters as a fallback. Use `push_to_hub_merged` to upload to your Hugging Face account! You can go to https://huggingface.co/settings/tokens for your personal tokens.

# In[16]:


# 保存为float16格式（用于VLLM）
# 支持merged_16bit（float16）、merged_4bit（int4）和lora适配器
if False: model.save_pretrained_merged("model", tokenizer, save_method = "merged_16bit",)
if False: model.push_to_hub_merged("hf/model", tokenizer, save_method = "merged_16bit", token = "")

