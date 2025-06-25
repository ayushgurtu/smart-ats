import os
import sys
import pandas as pd
from typing import List, Dict
import random
import json
import time
from datetime import datetime
from datasets import Dataset

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# RAGAS imports for multi-turn evaluation
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision
)

# Try to import additional metrics if available
try:
    from ragas.metrics import answer_correctness, answer_similarity
    ADVANCED_METRICS_AVAILABLE = True
except ImportError:
    ADVANCED_METRICS_AVAILABLE = False
    print("⚠️ Advanced metrics (answer_correctness, answer_similarity) not available in this RAGAS version")

# Try to import MultiTurnSample and message classes
try:
    from ragas import MultiTurnSample
    from ragas.messages import HumanMessage, AIMessage
    MULTITURN_SAMPLE_AVAILABLE = True
    print("✅ MultiTurnSample and message classes imported successfully")
except ImportError as e:
    MULTITURN_SAMPLE_AVAILABLE = False
    print(f"⚠️ MultiTurnSample not available - using simplified multi-turn evaluation: {e}")
    
    # Create simple replacement classes
    class HumanMessage:
        def __init__(self, content):
            self.content = content
    
    class AIMessage:
        def __init__(self, content):
            self.content = content
    
    class MultiTurnSample:
        def __init__(self, user_inputs, responses, retrieved_contexts, reference_contexts):
            self.user_inputs = user_inputs
            self.responses = responses
            self.retrieved_contexts = retrieved_contexts
            self.reference_contexts = reference_contexts

# Your RAG components
from rag.embeddings import get_embedding_function
from rag.vector_store import get_or_create_vector_store
from rag.retriever import get_retriever
from rag.llm_service import get_llm
from rag.rag_qa_chain import create_rag_chain, create_conversation_chain
from pages.faq_assistant import process_question

class RAGASMultiTurnEvaluator:
    def __init__(self, provider: str, model: str, data_path: str):
        self.provider = provider
        self.model = model
        self.data_path = data_path
        self.setup_rag_components()
        
    def setup_rag_components(self):
        """Initialize RAG components"""
        print(f"🔄 Setting up RAG components for {self.provider} - {self.model}...")
        self.embedding_function = get_embedding_function()
        self.vector_store = get_or_create_vector_store(self.embedding_function)
        self.retriever = get_retriever(self.vector_store, {"k": 5})
        self.llm = get_llm(provider=self.provider, model=self.model)
        self.qa_chain = create_conversation_chain(self.llm, self.retriever)  # Use conversation chain for multi-turn
        print("✅ RAG components ready!")
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4
    
    def create_multi_turn_conversations(self, df: pd.DataFrame, num_conversations: int = 20) -> List[MultiTurnSample]:
        """Create multi-turn conversation samples from job descriptions"""
        print(f"🎯 Creating {num_conversations} multi-turn conversations...")
        
        # Token tracking for rate limiting
        total_tokens_used = 0
        max_tokens_per_minute = 5000 if self.provider == "groq" else 10000  # Conservative limit
        
        # Sample jobs from dataset
        sampled_jobs = df.sample(n=min(num_conversations, len(df)))
        
        multi_turn_samples = []
        
        # Conversation templates for different career topics
        conversation_templates = [
            # Resume optimization conversation
            {
                "topic": "resume_optimization",
                "turns": [
                    "Hi, I need help optimizing my resume for {job_title} positions.",
                    "Can you be more specific about what skills I should highlight for {job_title}?",
                    "What about the formatting? Should I use a specific template for {job_title} applications?"
                ]
            },
            # Interview preparation conversation
            {
                "topic": "interview_preparation", 
                "turns": [
                    "I have an interview for a {job_title} position next week. How should I prepare?",
                    "What kind of technical questions should I expect for {job_title}?",
                    "Can you help me prepare some good questions to ask the interviewer about {job_title} roles?"
                ]
            },
            # Career transition conversation
            {
                "topic": "career_transition",
                "turns": [
                    "I want to transition to a {job_title} role. What should I focus on?",
                    "What skills should I develop first to become a {job_title}?",
                    "How long does transitioning to {job_title} typically take?"
                ]
            },
            # Salary negotiation conversation
            {
                "topic": "salary_negotiation",
                "turns": [
                    "I got an offer for a {job_title} position. How should I negotiate salary?",
                    "What's the typical salary range for {job_title} roles?",
                    "What other benefits should I consider besides salary for {job_title} positions?"
                ]
            },
            # Skills development conversation
            {
                "topic": "skills_development",
                "turns": [
                    "What are the most important skills for a {job_title}?",
                    "How can I develop these {job_title} skills effectively?",
                    "Are there any certifications that would help me as a {job_title}?"
                ]
            }
        ]
        
        for _, row in sampled_jobs.iterrows():
            job_title = row['Job Title']
            job_description = row['Job Description']
            
            # Create conversations for different templates
            template = random.choice(conversation_templates)
            
            # Format questions with job title
            user_inputs = [turn.format(job_title=job_title) for turn in template["turns"]]
            
            # Generate responses using RAG system
            responses = []
            contexts = []
            
            # Simulate conversation with memory
            conversation_history = []
            
            for i, user_input in enumerate(user_inputs):
                try:
                    # Enhanced rate limiting for Groq
                    if i > 0:
                        time.sleep(5.0)  # Longer delay between conversation turns
                    
                    # Add delay before each conversation (only between different conversations)
                    if len(multi_turn_samples) > 0 and i == 0:
                        time.sleep(3.0)  # Delay between conversations
                    
                    # Additional delay for Groq models due to TPM limits
                    if self.provider == "groq":
                        time.sleep(8.0)  # Extra delay for Groq to avoid TPM limits
                    
                    # Estimate tokens for this turn
                    estimated_tokens = self.estimate_tokens(user_input) + 500  # Add buffer for response
                    total_tokens_used += estimated_tokens
                    
                    # Check if we're approaching rate limits
                    if total_tokens_used > max_tokens_per_minute * 0.8:  # 80% of limit
                        print(f"⏳ Approaching token limit, waiting 60 seconds...")
                        time.sleep(60)
                        total_tokens_used = 0  # Reset counter
                    
                    # Process question with conversation memory
                    max_retries = 3
                    retry_delay = 10.0  # Start with 10 seconds
                    
                    for retry in range(max_retries):
                        try:
                            answer, sources, error = process_question(
                                user_input, 
                                self.qa_chain, 
                                "similarity", 
                                self.vector_store, 
                                {"k": 3},  # Reduced k to use fewer tokens
                                True,  # Enable memory for multi-turn
                                self.llm
                            )
                            
                            if error and "rate limit" in str(error).lower():
                                if retry < max_retries - 1:
                                    print(f"⏳ Rate limit hit, waiting {retry_delay} seconds before retry {retry + 1}...")
                                    time.sleep(retry_delay)
                                    retry_delay *= 2  # Exponential backoff
                                    continue
                                else:
                                    print(f"❌ Max retries reached for {job_title}, turn {i}")
                                    break
                            elif error:
                                print(f"⚠️ Error in conversation turn {i} for {job_title}: {error}")
                                break
                            else:
                                # Success - break out of retry loop
                                break
                                
                        except Exception as e:
                            if "rate limit" in str(e).lower() and retry < max_retries - 1:
                                print(f"⏳ Rate limit exception, waiting {retry_delay} seconds...")
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            else:
                                print(f"❌ Exception in turn {i} for {job_title}: {str(e)}")
                                error = str(e)
                                break
                    
                    # Skip if we have an error or empty response
                    if error or not answer or answer.strip() == "":
                        print(f"⚠️ Skipping turn {i} due to error or empty response")
                        break
                    
                    responses.append(str(answer))  # Ensure string format
                    
                    # Extract contexts from sources
                    turn_contexts = [doc.page_content for doc in sources] if sources else []
                    contexts.append(turn_contexts)
                    
                    # Update conversation history for next turn
                    conversation_history.extend([
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": answer}
                    ])
                    
                except Exception as e:
                    print(f"❌ Error processing turn {i} for {job_title}: {str(e)}")
                    break
            
            # Only add if we have complete conversations (at least 2 turns)
            if len(responses) >= 2 and all(r and r.strip() for r in responses):
                # Create MultiTurnSample with proper RAGAS format
                if MULTITURN_SAMPLE_AVAILABLE:
                    # Create conversation as alternating human/AI messages
                    user_input_messages = []
                    for i, (question, answer) in enumerate(zip(user_inputs[:len(responses)], responses)):
                        # Ensure all content is valid strings
                        question_str = str(question) if question else "No question"
                        answer_str = str(answer) if answer else "No answer"
                        
                        user_input_messages.append(HumanMessage(content=question_str))
                        user_input_messages.append(AIMessage(content=answer_str))
                    
                    multi_turn_sample = MultiTurnSample(
                        user_input=user_input_messages,
                        reference=str(job_description) if job_description else "No reference"
                    )
                else:
                    # Fallback to custom format for our simplified class
                    multi_turn_sample = MultiTurnSample(
                        user_inputs=user_inputs[:len(responses)],
                        responses=responses,
                        retrieved_contexts=contexts,
                        reference_contexts=[str(job_description)] * len(responses)
                    )
                
                multi_turn_samples.append(multi_turn_sample)
        
        print(f"✅ Created {len(multi_turn_samples)} multi-turn conversation samples")
        return multi_turn_samples
    
    def create_evaluation_dataset(self, multi_turn_samples: List[MultiTurnSample]) -> Dataset:
        """Convert MultiTurnSample objects to RAGAS dataset format"""
        print("🔄 Converting to RAGAS dataset format...")
        
        # Flatten multi-turn samples for evaluation
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for conv_id, sample in enumerate(multi_turn_samples):
            if MULTITURN_SAMPLE_AVAILABLE:
                # Extract questions and answers from RAGAS message format
                questions = []
                answers = []
                for i, message in enumerate(sample.user_input):
                    if hasattr(message, 'content'):
                        if i % 2 == 0:  # Even indices are human messages (questions)
                            questions.append(message.content)
                        else:  # Odd indices are AI messages (answers)
                            answers.append(message.content)
                
                # Add flattened conversation turns
                for turn_idx, (question, answer) in enumerate(zip(questions, answers)):
                    data["question"].append(str(question))  # Ensure string format
                    data["answer"].append(str(answer))      # Ensure string format
                    data["contexts"].append([])  # Empty contexts for multi-turn
                    data["ground_truth"].append(str(sample.reference or ""))  # Ensure string format
            else:
                # Use custom format
                for turn_idx in range(len(sample.user_inputs)):
                    data["question"].append(str(sample.user_inputs[turn_idx]))
                    data["answer"].append(str(sample.responses[turn_idx]))
                    data["contexts"].append(sample.retrieved_contexts[turn_idx] if sample.retrieved_contexts[turn_idx] else [])
                    data["ground_truth"].append(str(sample.reference_contexts[turn_idx] if turn_idx < len(sample.reference_contexts) else ""))
        
        # Ensure all lists have the same length
        min_length = min(len(data["question"]), len(data["answer"]), len(data["contexts"]), len(data["ground_truth"]))
        if min_length < len(data["question"]):
            print(f"⚠️ Trimming dataset to {min_length} items for consistency")
            for key in data:
                data[key] = data[key][:min_length]
        
        dataset = Dataset.from_dict(data)
        print(f"✅ Dataset created with {len(dataset)} conversation turns")
        return dataset
    
    def evaluate_with_ragas(self, dataset: Dataset):
        """Evaluate multi-turn RAG using RAGAS metrics"""
        print(f"🔍 Starting RAGAS multi-turn evaluation for {self.provider} - {self.model}...")
        
        # Define core metrics that are always available
        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
        
        # Add advanced metrics if available
        if ADVANCED_METRICS_AVAILABLE:
            try:
                from ragas.metrics import answer_correctness, answer_similarity
                metrics.extend([answer_correctness, answer_similarity])
                print("✅ Using advanced metrics (answer_correctness, answer_similarity)")
            except ImportError:
                print("⚠️ Advanced metrics not available, using core metrics only")
        else:
            print("ℹ️ Using core metrics only (faithfulness, answer_relevancy, context_precision, context_recall)")
        
        print(f"🧪 Evaluating with {len(metrics)} metrics...")
        
        # Configure RAGAS to use the same LLM as the one being evaluated
        # This avoids using OpenAI models during evaluation
        try:
            # Remove the problematic set_run_config calls - use simpler approach
            # Just use RAGAS with default settings to avoid compatibility issues
            print("ℹ️ Using RAGAS with default LLM settings for evaluation")
        except Exception as e:
            print(f"⚠️ Could not configure RAGAS to use {self.provider} model: {e}")
            print("ℹ️ RAGAS will use default OpenAI models for evaluation")
        
        # Run evaluation
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
        )
        
        return result
    
    def analyze_conversation_quality(self, multi_turn_samples: List[MultiTurnSample]):
        """Analyze conversation quality metrics"""
        print("📊 Analyzing conversation quality...")
        
        conversation_stats = {
            "total_conversations": len(multi_turn_samples),
            "total_turns": 0,
            "avg_turns_per_conversation": 0,
            "conversation_lengths": [],
            "topic_distribution": {}
        }
        
        total_turns = 0
        for sample in multi_turn_samples:
            if MULTITURN_SAMPLE_AVAILABLE:
                # Count human messages (questions) in RAGAS format
                turns = len([msg for i, msg in enumerate(sample.user_input) if i % 2 == 0])
                first_input = sample.user_input[0].content.lower() if sample.user_input else ""
            else:
                # Use custom format
                turns = len(sample.user_inputs)
                first_input = sample.user_inputs[0].lower() if sample.user_inputs else ""
            
            total_turns += turns
            conversation_stats["conversation_lengths"].append(turns)
            
            # Analyze topics based on first user input
            if "resume" in first_input:
                topic = "resume_optimization"
            elif "interview" in first_input:
                topic = "interview_preparation"
            elif "transition" in first_input:
                topic = "career_transition"
            elif "salary" in first_input or "negotiate" in first_input:
                topic = "salary_negotiation"
            elif "skills" in first_input:
                topic = "skills_development"
            else:
                topic = "general_career"
            
            conversation_stats["topic_distribution"][topic] = \
                conversation_stats["topic_distribution"].get(topic, 0) + 1
        
        conversation_stats["total_turns"] = total_turns
        conversation_stats["avg_turns_per_conversation"] = total_turns / len(multi_turn_samples) if multi_turn_samples else 0
        
        return conversation_stats
    
    def save_results(self, results, conversation_stats, output_dir: str):
        """Save RAGAS multi-turn evaluation results"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert results to DataFrame
        results_df = results.to_pandas()
        
        # Save detailed results
        csv_file = os.path.join(output_dir, f"ragas_{self.provider}_{self.model.replace('-', '_')}_detailed.csv")
        results_df.to_csv(csv_file, index=False)
        
        # Create comprehensive summary
        summary = {
            "model_info": {
                "provider": self.provider,
                "model": self.model,
                "evaluation_timestamp": datetime.now().isoformat(),
                "framework": "ragas_multiturn"
            },
            "evaluation_type": "multi_turn_conversation",
            "total_turns_evaluated": len(results_df),
            "conversation_stats": conversation_stats,
            "metrics_summary": {}
        }
        
        # Calculate metric statistics
        metric_columns = [col for col in results_df.columns 
                         if col not in ['question', 'answer', 'contexts', 'ground_truth']]
        
        for metric in metric_columns:
            if metric in results_df.columns:
                scores = results_df[metric].dropna()
                if len(scores) > 0:
                    summary["metrics_summary"][metric] = {
                        "average_score": float(scores.mean()),
                        "min_score": float(scores.min()),
                        "max_score": float(scores.max()),
                        "std_score": float(scores.std()),
                        "median_score": float(scores.median()),
                        "total_evaluations": len(scores)
                    }
        
        # Save summary
        summary_file = os.path.join(output_dir, f"ragas_{self.provider}_{self.model.replace('-', '_')}_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"💾 RAGAS results saved to {csv_file}")
        print(f"📊 Summary saved to {summary_file}")
        
        return summary, csv_file, summary_file
    
    def run_evaluation(self, num_conversations: int = 20):
        """Run complete RAGAS multi-turn evaluation"""
        # Load dataset
        df = pd.read_csv(self.data_path)
        print(f"📊 Loaded {len(df)} job descriptions")
        
        # Create multi-turn conversation samples
        multi_turn_samples = self.create_multi_turn_conversations(df, num_conversations)
        
        if not multi_turn_samples:
            print("❌ No multi-turn samples created. Evaluation cannot proceed.")
            return None, None
        
        # Analyze conversation quality
        conversation_stats = self.analyze_conversation_quality(multi_turn_samples)
        
        # Convert to dataset format
        eval_dataset = self.create_evaluation_dataset(multi_turn_samples)
        
        # Run evaluation
        results = self.evaluate_with_ragas(eval_dataset)
        
        # Save results
        output_dir = os.path.join(os.path.dirname(__file__), "results", "ragas")
        summary, csv_file, summary_file = self.save_results(results, conversation_stats, output_dir)
        
        return results, summary
