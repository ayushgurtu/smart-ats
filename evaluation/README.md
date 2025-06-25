# Smart ATS FAQ Assistant - Evaluation Framework

Comprehensive evaluation framework using **DeepEval** and **RAGAS** for the Smart ATS FAQ Assistant.

## 📊 Evaluation Results Summary

### RAGAS Multi-Turn Evaluation ✅ COMPLETE
| Model | Overall Score | Answer Relevancy | Faithfulness | Context Precision | Context Recall |
|-------|---------------|------------------|--------------|-------------------|----------------|
| 🏆 **OpenAI GPT-3.5-Turbo** | **0.498** | 0.810 | 0.710 | 0.294 | 0.179 |
| 🥈 **Groq Llama-3.1-8B-Instant** | **0.418** | **0.941** | 0.534 | 0.220 | 0.075 |
| 🥉 **OpenAI GPT-4o-Mini** | **0.386** | 0.743 | **0.866** | 0.255 | 0.182 |
| **Groq Llama3-8B-8192** | **0.383** | 0.891 | 0.464 | 0.220 | 0.056 |

### DeepEval Single-Turn Evaluation ✅ COMPLETE
| Model | Average Score | Status |
|-------|---------------|--------|
| 🏆 **Groq Llama-3.1-8B-Instant** | **1.000** | ✅ Complete |
| 🏆 **OpenAI GPT-3.5-Turbo** | **1.000** | ✅ Complete |
| 🏆 **OpenAI GPT-4o-Mini** | **1.000** | ✅ Complete |
| **Groq Llama3-8B-8192** | **0.946** | ✅ Complete |

## 🏗️ Framework Overview

### DeepEval Framework ✅
- **Purpose**: Single-turn Q&A evaluation using actual dataset
- **Metrics**: Answer Relevancy, Faithfulness 
- **Data Source**: job_title_des.csv (same as RAGAS)
- **Test Cases**: Configurable (default: 2 per model)

### RAGAS Framework ✅
- **Purpose**: Multi-turn conversation evaluation
- **Metrics**: Faithfulness, Answer Relevancy, Context Precision, Context Recall, Answer Correctness, Answer Similarity
- **Conversations**: Multi-turn conversations per model (default: 1 per model for testing)

---

## 📋 **Step-by-Step Evaluation Process**

### **Phase 1: RAGAS Multi-Turn Conversation Evaluation**

#### **Step 1: Environment Setup**
```python
# Initialize RAG components for each model
embedding_function = get_embedding_function()
vector_store = get_or_create_vector_store(embedding_function)
retriever = get_retriever(vector_store, {"k": 5})  # Retrieve top 5 relevant documents
llm = get_llm(provider=provider, model=model)
qa_chain = create_conversation_chain(llm, retriever)  # Multi-turn capable chain
```

#### **Step 2: Dataset Loading**
```python
# Load job descriptions dataset (same as used for vector store)
df = pd.read_csv("../data/job_title_des.csv")
sampled_jobs = df.sample(n=num_conversations)  # Sample jobs for conversation topics
```

#### **Step 3: Multi-Turn Conversation Generation**
**Conversation Templates Used:**
1. **Resume Optimization** (3 turns):
   - "Hi, I need help optimizing my resume for {job_title} positions."
   - "Can you be more specific about what skills I should highlight for {job_title}?"
   - "What about the formatting? Should I use a specific template for {job_title} applications?"

2. **Interview Preparation** (3 turns):
   - "I have an interview for a {job_title} position next week. How should I prepare?"
   - "What kind of technical questions should I expect for {job_title}?"
   - "Can you help me prepare some good questions to ask the interviewer about {job_title} roles?"

3. **Career Transition** (3 turns):
   - "I want to transition to a {job_title} role. What should I focus on?"
   - "What skills should I develop first to become a {job_title}?"
   - "How long does transitioning to {job_title} typically take?"

4. **Salary Negotiation** (3 turns):
   - "I got an offer for a {job_title} position. How should I negotiate salary?"
   - "What's the typical salary range for {job_title} roles?"
   - "What other benefits should I consider besides salary for {job_title} positions?"

5. **Skills Development** (3 turns):
   - "What are the most important skills for a {job_title}?"
   - "How can I develop these {job_title} skills effectively?"
   - "Are there any certifications that would help me as a {job_title}?"

#### **Step 4: RAG Response Generation**
```python
# For each conversation turn:
conversation_history = []  # Maintain context across turns
for user_input in conversation_turns:
    response = qa_chain.invoke({
        "question": user_input,
        "chat_history": conversation_history
    })
    
    # Extract response and retrieved documents
    ai_response = response["answer"]
    retrieved_contexts = [doc.page_content for doc in response["source_documents"]]
    
    # Update conversation history
    conversation_history.extend([
        HumanMessage(content=user_input),
        AIMessage(content=ai_response)
    ])
```

#### **Step 5: RAGAS Dataset Creation**
```python
# Convert conversations to RAGAS format
dataset_data = {
    "question": [],      # User questions from all conversation turns
    "answer": [],        # AI responses from all conversation turns  
    "contexts": [],      # Retrieved documents for each turn
    "ground_truth": []   # Reference contexts from job descriptions
}

# Create HuggingFace Dataset
dataset = Dataset.from_dict(dataset_data)
```

#### **Step 6: RAGAS Metrics Evaluation**
**Core Metrics Applied:**
1. **Faithfulness** (0-1): Measures if the answer is grounded in the retrieved context
2. **Answer Relevancy** (0-1): Measures how relevant the answer is to the question
3. **Context Precision** (0-1): Measures precision of retrieved context
4. **Context Recall** (0-1): Measures recall of retrieved context
5. **Answer Correctness** (0-1): Measures factual correctness (if available)
6. **Answer Similarity** (0-1): Measures semantic similarity to ground truth (if available)

```python
# Run RAGAS evaluation
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall, 
             answer_correctness, answer_similarity],  # Last 2 if available
    llm=llm,  # Use same LLM for evaluation consistency
    embeddings=embedding_function
)
```

#### **Step 7: Results Processing & Storage**
- Save detailed results to CSV: `ragas_{provider}_{model}_detailed.csv`
- Calculate aggregate statistics (mean, min, max, std dev)
- Generate performance summaries and rankings

---

### **Phase 2: DeepEval Single-Turn Q&A Evaluation**

#### **Step 1: Environment Setup**
```python
# Initialize RAG components (same as RAGAS)
embedding_function = get_embedding_function()
vector_store = get_or_create_vector_store(embedding_function)
retriever = get_retriever(vector_store, {"k": 3})  # Fewer docs for single-turn
llm = get_llm(provider=provider, model=model)
qa_chain = create_conversation_chain(llm, retriever)
```

#### **Step 2: Test Case Generation from Dataset**
```python
# Sample job descriptions for realistic questions
sample_jobs = df.sample(min(num_cases, len(df)))

for job_row in sample_jobs:
    job_title = job_row['Job Title']
    skills = job_row['Key Skills'].split(',')[:3]  # First 3 skills
    
    # Create realistic question
    question = f"What skills are needed for a {job_title} role?"
    
    # Create expected answer from job data
    expected_answer = f"For a {job_title} role, key skills include: {', '.join(skills)}."
```

#### **Step 3: RAG Response Generation**
```python
# Get single-turn response (no conversation history)
response = qa_chain.invoke({
    "question": question,
    "chat_history": []  # Empty for single-turn
})

actual_answer = response["answer"]
retrieved_contexts = [doc.page_content[:300] for doc in response["source_documents"][:2]]
```

#### **Step 4: DeepEval Test Case Creation**
```python
test_case = LLMTestCase(
    input=question,                    # User question
    actual_output=actual_answer,       # RAG system response
    expected_output=expected_answer,   # Ground truth from dataset
    retrieval_context=retrieved_contexts  # Retrieved document contexts
)
```

#### **Step 5: DeepEval Metrics Evaluation**
**Metrics Applied:**
1. **Answer Relevancy Metric** (threshold=0.5):
   - Measures how relevant the answer is to the question
   - Uses semantic similarity and keyword matching
   
2. **Faithfulness Metric** (threshold=0.5):
   - Measures if the answer is faithful to the retrieved context
   - Checks for hallucinations or contradictions

```python
metrics = [
    AnswerRelevancyMetric(threshold=0.5),
    FaithfulnessMetric(threshold=0.5)
]

# Run evaluation with rate limiting
results = evaluate(
    test_cases=test_cases,
    metrics=metrics,
    hyperparameters={"concurrent_api_calls": 1}  # Avoid rate limits
)
```

#### **Step 6: Results Aggregation**
```python
# Process results for each metric
for test_result in results.test_results:
    for metric_data in test_result.metrics_data:
        metric_name = metric_data.metric.__class__.__name__
        score = float(metric_data.score)
        
        # Aggregate scores: average, min, max
        metric_scores[metric_name].append(score)
```

---

## 🔬 **Evaluation Methodology Details**

### **Data Sources**
- **Primary Dataset**: `job_title_des.csv` (2,484 job descriptions)
- **Vector Store**: Pre-built embeddings from job descriptions using sentence-transformers
- **Ground Truth**: Actual job requirements and skills from dataset

### **Rate Limiting & API Management**
- **RAGAS**: 3-8 second delays between conversation turns (especially for Groq models)
- **DeepEval**: 10+ second delays between test cases, 60 seconds between models
- **Groq Models**: Extra delays due to TPM (tokens per minute) limits
- **OpenAI Models**: Standard rate limiting with exponential backoff

### **Quality Assurance**
- **Token Estimation**: Pre-estimate API calls to avoid rate limits
- **Error Handling**: Retry logic with exponential backoff
- **Data Validation**: Ensure consistent dataset formats across frameworks
- **Result Validation**: Cross-check metric calculations and aggregations

### **Evaluation Scale**
- **RAGAS**: 3 multi-turn conversations per model = ~9 total Q&A pairs per model
- **DeepEval**: 1-2 single-turn Q&A pairs per model
- **Total Test Cases**: ~40+ individual evaluations across 4 models

---
## � **Detailed Metrics Explanation**

### **RAGAS Metrics (Multi-Turn Evaluation)**

| Metric | Scale | Description | What It Measures |
|--------|-------|-------------|------------------|
| **Faithfulness** | 0-1 | Answer grounding in context | How well the answer stays true to retrieved documents without hallucination |
| **Answer Relevancy** | 0-1 | Answer relevance to question | How well the answer addresses the specific question asked |
| **Context Precision** | 0-1 | Retrieval precision | How many of the retrieved documents are actually relevant to the question |
| **Context Recall** | 0-1 | Retrieval recall | How many of the relevant documents were successfully retrieved |
| **Answer Correctness** | 0-1 | Factual accuracy | How factually correct the answer is compared to ground truth |
| **Answer Similarity** | 0-1 | Semantic similarity | How semantically similar the answer is to the expected response |

### **DeepEval Metrics (Single-Turn Evaluation)**

| Metric | Scale | Description | What It Measures |
|--------|-------|-------------|------------------|
| **Answer Relevancy** | 0-1 | Question-answer relevance | How well the answer addresses the input question |
| **Faithfulness** | 0-1 | Context faithfulness | How faithful the answer is to the retrieved context |

### **Scoring Interpretation**

| Score Range | Performance Level | Interpretation |
|-------------|-------------------|----------------|
| **0.8 - 1.0** | 🟢 Excellent | Production-ready performance |
| **0.6 - 0.79** | 🟡 Good | Acceptable with minor improvements needed |
| **0.4 - 0.59** | 🟠 Fair | Needs significant improvement |
| **0.0 - 0.39** | 🔴 Poor | Critical issues, major improvements required |

---

## �📁 File Structure

```
evaluation/
├── deepeval_evaluation_runner.py           # DeepEval execution script
├── ragas_evaluation_runner.py              # RAGAS execution script wrapper
├── ragas_evaluator.py                      # RAGAS core evaluation logic
├── ragas_results_processor.py              # Results analysis & visualization
├── README.md                               # This documentation
└── results/                                # All evaluation results
    ├── deepeval/
    │   └── deepeval_results.json           # DeepEval results (4 models)
    ├── ragas/
    │   ├── ragas_groq_llama3_8b_8192_detailed.csv
    │   ├── ragas_groq_llama_3.1_8b_instant_detailed.csv
    │   ├── ragas_openai_gpt_3.5_turbo_detailed.csv
    │   └── ragas_openai_gpt_4o_mini_detailed.csv
    ├── RAGAS_Evaluation_Report.md          # RAGAS framework detailed results
    ├── DeepEval_Evaluation_Report.md       # DeepEval framework detailed results
    ├── Final_Evaluation_Summary.md         # Combined analysis & recommendations
    ├── comprehensive_evaluation_summary.json
    └── *.png                               # Visualization charts
```

## ⚡ **EXECUTION COMMANDS**

### **Complete Evaluation (Recommended)**
```bash
cd /Users/vishalmishra/MyDocuments/SMU_MITB/Term-3/Gen_AI_with_LLM/Project/Smart_ATS_With_RAG && pipenv shell && cd evaluation
python ragas_evaluation_runner.py          # ~30-45 minutes
python deepeval_evaluation_runner.py       # ~10-15 minutes  
python ragas_results_processor.py          # ~2-3 minutes
```

### **Individual Commands**
```bash
# Setup environment
cd /Users/vishalmishra/MyDocuments/SMU_MITB/Term-3/Gen_AI_with_LLM/Project/Smart_ATS_With_RAG && pipenv shell && cd evaluation

# Run RAGAS evaluation
python ragas_evaluation_runner.py

# Run DeepEval evaluation (default: 2 test cases per model)
python deepeval_evaluation_runner.py

# Custom test cases
python deepeval_evaluation_runner.py --num-cases 3

# Process results and generate reports
python ragas_results_processor.py
```

### **One-Liner for Complete Evaluation**
```bash
cd /Users/vishalmishra/MyDocuments/SMU_MITB/Term-3/Gen_AI_with_LLM/Project/Smart_ATS_With_RAG && pipenv shell && cd evaluation && python ragas_evaluation_runner.py && python deepeval_evaluation_runner.py && python ragas_results_processor.py
```

## � Key Findings

### **Overall Performance**
1. **RAGAS Multi-Turn**: OpenAI GPT-3.5-Turbo leads with balanced performance (0.498)
2. **DeepEval Single-Turn**: Three models achieve perfect scores (1.0)
3. **Answer Relevancy**: Groq models excel in question understanding
4. **Faithfulness**: OpenAI models show stronger context grounding

### **Model Recommendations**
- **Best Overall**: OpenAI GPT-3.5-Turbo (consistent across both frameworks)
- **Cost-Effective**: Groq Llama-3.1-8B-Instant (high relevancy, lower cost)
- **High Precision**: OpenAI GPT-4o-Mini (highest faithfulness in RAGAS)

## � **Detailed Reports**

### **Framework-Specific Reports**
- **[RAGAS Evaluation Report](./results/RAGAS_Evaluation_Report.md)** - Multi-turn conversation analysis
- **[DeepEval Evaluation Report](./results/DeepEval_Evaluation_Report.md)** - Single-turn Q&A analysis

### **Final Summary**
- **[Final Evaluation Summary](./results/Final_Evaluation_Summary.md)** - Combined results, recommendations, and deployment guide

## �🔧 Prerequisites

**Environment Setup**: Ensure API keys in `.env` file:
```bash
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
```

**Dependencies**: 
```bash
cd /Users/vishalmishra/MyDocuments/SMU_MITB/Term-3/Gen_AI_with_LLM/Project/Smart_ATS_With_RAG
pipenv install && pipenv shell
```

---

**Status**: ✅ All Evaluations Complete | 📊 Results Available | 📈 Reports Generated  
**Last Updated**: June 19, 2025
