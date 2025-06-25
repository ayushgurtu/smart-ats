#!/usr/bin/env python3
"""
DeepEval evaluation for Smart ATS FAQ Assistant
Uses actual dataset for ground truth like RAGAS
"""

import os
import sys
import pandas as pd
import json
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import DeepEval components
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

# RAG components
from rag.embeddings import get_embedding_function
from rag.vector_store import get_or_create_vector_store
from rag.retriever import get_retriever
from rag.llm_service import get_llm
from rag.rag_qa_chain import create_conversation_chain
from pages.faq_assistant import process_question

class DeepEvalEvaluator:
    def __init__(self, provider: str, model: str, data_path: str):
        self.provider = provider
        self.model = model
        self.data_path = data_path
        self.setup_rag()
        self.load_dataset()
    
    def setup_rag(self):
        """Setup RAG components"""
        print(f"🔄 Setting up RAG for {self.provider} - {self.model}...")
        
        try:
            self.embedding_function = get_embedding_function()
            self.vector_store = get_or_create_vector_store(self.embedding_function)
            self.retriever = get_retriever(self.vector_store, {"k": 3})
            self.llm = get_llm(provider=self.provider, model=self.model)
            self.qa_chain = create_conversation_chain(self.llm, self.retriever)
            print("✅ RAG setup complete")
        except Exception as e:
            print(f"❌ RAG setup failed: {str(e)}")
            raise
    
    def load_dataset(self):
        """Load job descriptions dataset"""
        try:
            self.df = pd.read_csv(self.data_path)
            print(f"✅ Loaded {len(self.df)} job descriptions")
        except Exception as e:
            print(f"❌ Failed to load dataset: {str(e)}")
            raise
    
    def create_test_cases(self, num_cases=2):
        """Create test cases from actual dataset"""
        test_cases = []
        
        # Sample job descriptions for questions
        sample_jobs = self.df.sample(min(num_cases, len(self.df)))
        
        for i, (_, job_row) in enumerate(sample_jobs.iterrows(), 1):
            print(f"📝 Creating test case {i}/{num_cases}")
            
            # Create realistic question from job description
            job_title = job_row.get('Job Title', 'Software Developer')
            skills = str(job_row.get('Key Skills', '')).split(',')[:3]  # Take first 3 skills
            
            question = f"What skills are needed for a {job_title} role?"
            
            # Create expected answer from job data
            expected_answer = f"For a {job_title} role, key skills include: {', '.join(skills)}."
            
            # Get RAG response
            try:
                response = self.qa_chain.invoke({
                    "question": question,
                    "chat_history": []
                })
                
                answer = response.get("answer", str(response)) if isinstance(response, dict) else str(response)
                sources = response.get("source_documents", []) if isinstance(response, dict) else []
                
                # Create context from sources
                contexts = [doc.page_content[:300] for doc in sources[:2]] if sources else []
                
                # Create test case
                test_case = LLMTestCase(
                    input=question,
                    actual_output=answer,
                    expected_output=expected_answer,
                    retrieval_context=contexts
                )
                
                test_cases.append(test_case)
                print(f"  ✅ Created test case: {question[:50]}...")
                
                # Small delay between test cases
                time.sleep(2)
                
            except Exception as e:
                print(f"  ❌ Failed to create test case {i}: {str(e)}")
                continue
        
        print(f"✅ Created {len(test_cases)} test cases")
        return test_cases
    
    def run_evaluation(self, test_cases):
        """Run DeepEval evaluation"""
        if not test_cases:
            return None
            
        print(f"🔍 Running DeepEval with {len(test_cases)} test cases...")
        
        try:
            metrics = [
                AnswerRelevancyMetric(threshold=0.5),
                FaithfulnessMetric(threshold=0.5)
            ]
            
            # Wait before evaluation
            wait_time = 10 + (len(test_cases) * 2)
            print(f"⏳ Waiting {wait_time} seconds to avoid rate limits...")
            time.sleep(wait_time)
            
            results = evaluate(
                test_cases=test_cases,
                metrics=metrics,
                hyperparameters={"concurrent_api_calls": 1}
            )
            
            return results
            
        except Exception as e:
            print(f"❌ Evaluation failed: {str(e)}")
            return None
    
    def process_results(self, results, num_cases):
        """Process evaluation results"""
        if not results or not results.test_results:
            return {
                "provider": self.provider,
                "model": self.model,
                "status": "failed",
                "error": "No results generated"
            }
        
        # Process metrics
        summary = {
            "provider": self.provider,
            "model": self.model,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "framework": "deepeval",
            "total_test_cases": len(results.test_results),
            "requested_test_cases": num_cases,
            "metrics": {}
        }
        
        # Aggregate metrics
        metric_scores = {}
        
        for test_result in results.test_results:
            for metric_data in test_result.metrics_data:
                try:
                    metric_name = metric_data.metric.__class__.__name__ if hasattr(metric_data, 'metric') else "Unknown"
                    score = float(metric_data.score)
                    
                    if metric_name not in metric_scores:
                        metric_scores[metric_name] = []
                    metric_scores[metric_name].append(score)
                    
                except Exception as e:
                    print(f"⚠️ Warning: Could not process metric: {e}")
        
        # Calculate averages
        for metric_name, scores in metric_scores.items():
            if scores:
                summary["metrics"][metric_name] = {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "total_cases": len(scores)
                }
        
        return summary

def test_single_model(provider: str, model: str, num_cases=2, data_path=None):
    """Test a single model with DeepEval"""
    
    if not data_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, "..", "data", "job_title_des.csv")
        data_path = os.path.abspath(data_path)
    
    if not os.path.exists(data_path):
        print(f"❌ Dataset not found: {data_path}")
        return {
            "provider": provider,
            "model": model,
            "status": "failed",
            "error": "Dataset not found"
        }
    
    print(f"\n🧪 DeepEval: {provider.upper()} - {model}")
    print(f"📊 Test Cases: {num_cases}")
    print("=" * 60)
    
    try:
        # Create evaluator
        evaluator = DeepEvalEvaluator(provider, model, data_path)
        
        # Create test cases
        test_cases = evaluator.create_test_cases(num_cases)
        if not test_cases:
            return {
                "provider": provider,
                "model": model,
                "status": "failed",
                "error": "Could not create test cases"
            }
        
        # Run evaluation
        results = evaluator.run_evaluation(test_cases)
        if not results:
            return {
                "provider": provider,
                "model": model,
                "status": "failed", 
                "error": "Evaluation failed"
            }
        
        # Process results
        summary = evaluator.process_results(results, num_cases)
        
        # Print results
        print(f"\n📊 Results for {provider.upper()} - {model}:")
        if summary["status"] == "completed":
            print(f"✅ Completed {summary['total_test_cases']}/{summary['requested_test_cases']} test cases")
            for metric_name, metric_data in summary["metrics"].items():
                avg_score = metric_data["average_score"]
                print(f"  📈 {metric_name}: {avg_score:.3f} (range: {metric_data['min_score']:.3f}-{metric_data['max_score']:.3f})")
        else:
            print(f"  ❌ {summary.get('error', 'Unknown error')}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Failed to test {provider} - {model}: {str(e)}")
        return {
            "provider": provider,
            "model": model,
            "status": "failed",
            "error": str(e)
        }

def main(num_cases=2):
    """Run DeepEval for all models"""
    
    models = [
        ("groq", "llama3-8b-8192"),
        ("groq", "llama-3.1-8b-instant"),
        ("openai", "gpt-3.5-turbo"),
        ("openai", "gpt-4o-mini")
    ]
    
    print("🚀 DeepEval Testing")
    print("=" * 60)
    print(f"🎯 {num_cases} test cases per model")
    print(f"📊 Using actual dataset for ground truth")
    print("=" * 60)
    
    all_results = {
        "test_timestamp": datetime.now().isoformat(),
        "test_type": "deepeval",
        "configuration": {
            "test_cases_per_model": num_cases,
            "total_models": len(models)
        },
        "model_results": {}
    }
    
    for i, (provider, model) in enumerate(models, 1):
        print(f"\n🔄 Model {i}/{len(models)}")
        
        result = test_single_model(provider, model, num_cases)
        model_key = f"{provider}_{model}"
        all_results["model_results"][model_key] = result
        
        # Wait between models
        if i < len(models):
            wait_time = 60
            print(f"⏳ Waiting {wait_time} seconds before next model...")
            time.sleep(wait_time)
    
    # Save results
    results_dir = os.path.join(os.path.dirname(__file__), "results", "deepeval")
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = os.path.join(results_dir, f"deepeval_results.json")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 DEEPEVAL SUMMARY ({num_cases} test cases per model)")
    print("=" * 60)
    
    for model_key, result in all_results["model_results"].items():
        provider, model = model_key.split("_", 1)
        status = result["status"]
        
        if status == "completed":
            completed_cases = result.get("total_test_cases", 0)
            print(f"✅ {provider.upper():>8} {model:<20} - {completed_cases}/{num_cases} cases")
            if "metrics" in result:
                for metric_name, metric_data in result["metrics"].items():
                    avg_score = metric_data["average_score"]
                    print(f"     📈 {metric_name}: {avg_score:.3f}")
        else:
            print(f"❌ {provider.upper():>8} {model:<20} - FAILED")
            if "error" in result:
                print(f"     Error: {result['error']}")
    
    print(f"\n💾 Results saved to: {results_file}")
    print("🎉 DeepEval completed!")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run DeepEval evaluation')
    parser.add_argument('--num-cases', '-n', type=int, default=2, 
                        help='Number of test cases per model (default: 2)')
    
    args = parser.parse_args()
    main(args.num_cases)
