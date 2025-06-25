#!/usr/bin/env python3
"""
RAGAS Evaluation Runner for Smart ATS FAQ Assistant
Runs RAGAS multi-turn conversation evaluation for all models
"""

import os
import sys
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ragas_evaluator import RAGASMultiTurnEvaluator

def run_ragas_evaluation_single_model(provider: str, model: str, num_conversations: int = 1):
    """Run RAGAS evaluation for a single model"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "..", "data", "job_title_des.csv")
    data_path = os.path.abspath(data_path)
    
    if not os.path.exists(data_path):
        print(f"❌ Dataset not found: {data_path}")
        return False
    
    print(f"🚀 Running RAGAS Evaluation: {provider.upper()} - {model}")
    print("=" * 60)
    
    try:
        evaluator = RAGASMultiTurnEvaluator(provider, model, data_path)
        print(f"📈 Starting RAGAS evaluation with {num_conversations} conversation(s)...")
        
        results, summary = evaluator.run_evaluation(num_conversations)
        
        if summary:
            print(f"✅ RAGAS evaluation completed for {provider} - {model}")
            print(f"📊 Results saved in: evaluation/results/ragas/")
            
            # Print key metrics
            if "metrics_summary" in summary:
                print("\n📈 Key Metrics:")
                for metric, stats in summary["metrics_summary"].items():
                    score = stats.get("average_score", 0)
                    print(f"  • {metric}: {score:.3f}")
            return True
        else:
            print(f"❌ RAGAS evaluation failed for {provider} - {model}")
            return False
            
    except Exception as e:
        print(f"❌ Error during RAGAS evaluation: {str(e)}")
        return False

def run_ragas_evaluation_all_models(num_conversations: int = 1):
    """Run RAGAS evaluation for all supported models"""
    
    models_to_test = [
        ("groq", "llama3-8b-8192"),
        ("groq", "llama-3.1-8b-instant"),
        ("openai", "gpt-3.5-turbo"),
        ("openai", "gpt-4o-mini")
    ]
    
    print("🚀 RAGAS Multi-turn Conversation Evaluation")
    print("=" * 60)
    print(f"🎯 Testing {len(models_to_test)} models")
    print(f"💬 {num_conversations} conversation(s) per model")
    print(f"📊 6 RAGAS metrics per evaluation")
    print("=" * 60)
    
    results_summary = {
        "test_timestamp": datetime.now().isoformat(),
        "framework": "ragas",
        "total_models_tested": len(models_to_test),
        "num_conversations_per_model": num_conversations,
        "results": {}
    }
    
    successful_evaluations = 0
    
    for i, (provider, model) in enumerate(models_to_test, 1):
        print(f"\n🔄 Model {i}/{len(models_to_test)}")
        
        start_time = time.time()
        success = run_ragas_evaluation_single_model(provider, model, num_conversations)
        end_time = time.time()
        
        duration = end_time - start_time
        model_key = f"{provider}_{model}"
        
        results_summary["results"][model_key] = {
            "provider": provider,
            "model": model,
            "success": success,
            "duration_seconds": duration,
            "completed_at": datetime.now().isoformat()
        }
        
        if success:
            successful_evaluations += 1
        
        # Wait between models to avoid rate limits
        if i < len(models_to_test):
            wait_time = 30  # 30 seconds between models
            print(f"⏳ Waiting {wait_time} seconds before next model...")
            time.sleep(wait_time)
    
    # Save overall summary
    summary_path = os.path.join(os.path.dirname(__file__), "results", "ragas_evaluation_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    # Print final summary
    print(f"\n{'='*60}")
    print("📊 RAGAS EVALUATION SUMMARY")
    print("="*60)
    print(f"✅ Successful: {successful_evaluations}/{len(models_to_test)} models")
    print(f"⏱️  Total time: {sum(r['duration_seconds'] for r in results_summary['results'].values()):.1f} seconds")
    print(f"📁 Summary saved: {summary_path}")
    
    if successful_evaluations > 0:
        print(f"\n🎉 RAGAS evaluation completed!")
        print(f"📊 Next step: Run 'python ragas_results_processor.py' to generate charts and analysis")
    else:
        print(f"\n❌ No evaluations completed successfully")
    
    return results_summary

def main():
    """Main entry point"""
    print("🎯 Smart ATS FAQ Assistant - RAGAS Evaluation Runner")
    
    # Check if user wants to run all models or single model
    import argparse
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    parser.add_argument("--provider", type=str, help="Model provider (groq/openai)")
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--conversations", type=int, default=1, help="Number of conversations per model")
    
    args = parser.parse_args()
    
    if args.provider and args.model:
        # Single model evaluation
        success = run_ragas_evaluation_single_model(args.provider, args.model, args.conversations)
        if success:
            print("\n🎉 Single model evaluation completed!")
        else:
            print("\n❌ Single model evaluation failed!")
    else:
        # All models evaluation
        run_ragas_evaluation_all_models(args.conversations)

if __name__ == "__main__":
    main()