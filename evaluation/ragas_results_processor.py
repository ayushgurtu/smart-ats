#!/usr/bin/env python3
"""
Process CSV results and generate comprehensive presentation
"""

import os
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np

def process_csv_results():
    """Process CSV files and generate comprehensive presentation"""
    
    results_dir = os.path.join(os.path.dirname(__file__), "results", "ragas")
    
    # Find all CSV files
    csv_files = [f for f in os.listdir(results_dir) if f.endswith("_detailed.csv")]
    
    if not csv_files:
        print("❌ No CSV result files found")
        return
    
    print(f"📊 Found {len(csv_files)} result files")
    
    model_results = {}
    all_metrics = set()
    
    # Process each CSV file
    for csv_file in csv_files:
        print(f"🔄 Processing {csv_file}")
        
        # Extract model info from filename
        # Format: ragas_provider_model_detailed.csv
        parts = csv_file.replace("ragas_", "").replace("_detailed.csv", "").split("_")
        if len(parts) >= 2:
            provider = parts[0]
            model = "_".join(parts[1:])  # Join remaining parts for model name
        else:
            continue
        
        file_path = os.path.join(results_dir, csv_file)
        
        try:
            df = pd.read_csv(file_path)
            
            # Get numeric columns (metrics)
            metric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            all_metrics.update(metric_columns)
            
            # Calculate statistics for each metric
            model_key = f"{provider}_{model}"
            model_results[model_key] = {
                "provider": provider,
                "model": model,
                "total_evaluations": len(df),
                "metrics": {}
            }
            
            for metric in metric_columns:
                scores = df[metric].dropna()
                if len(scores) > 0:
                    model_results[model_key]["metrics"][metric] = {
                        "average_score": float(scores.mean()),
                        "min_score": float(scores.min()),
                        "max_score": float(scores.max()),
                        "std_score": float(scores.std()),
                        "median_score": float(scores.median()),
                        "total_evaluations": len(scores)
                    }
            
            print(f"  ✅ Processed {len(df)} evaluations with {len(metric_columns)} metrics")
            
        except Exception as e:
            print(f"  ❌ Error processing {csv_file}: {str(e)}")
    
    if not model_results:
        print("❌ No valid results processed")
        return
    
    # Create comprehensive summary
    presentation_data = {
        "evaluation_summary": {
            "timestamp": datetime.now().isoformat(),
            "total_models_evaluated": len(model_results),
            "evaluation_framework": "RAGAS Multi-turn Conversations",
            "metrics_evaluated": list(all_metrics)
        },
        "model_performance": model_results
    }
    
    # Save comprehensive results
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    
    # Save JSON summary
    summary_file = os.path.join(output_dir, "comprehensive_evaluation_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(presentation_data, f, indent=2)
    
    # Create detailed markdown report
    create_markdown_report(presentation_data, output_dir)
    
    # Create performance comparison charts
    create_performance_charts(presentation_data, output_dir)
    
    # Print console summary
    print_console_summary(presentation_data)
    
    print(f"\n✅ Comprehensive presentation created!")
    print(f"📊 Summary: {summary_file}")
    
    return presentation_data

def create_markdown_report(data, output_dir):
    """Create detailed markdown report"""
    
    report_file = os.path.join(output_dir, "Smart_ATS_Model_Evaluation_Report.md")
    
    with open(report_file, 'w') as f:
        f.write("# Smart ATS FAQ Assistant - Model Evaluation Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Evaluation Framework:** {data['evaluation_summary']['evaluation_framework']}\n\n")
        f.write(f"**Models Evaluated:** {data['evaluation_summary']['total_models_evaluated']}\n\n")
        f.write(f"**Metrics:** {', '.join(data['evaluation_summary']['metrics_evaluated'])}\n\n")
        
        f.write("## Executive Summary\n\n")
        
        # Find best performing model for each metric
        best_performers = {}
        for metric in data['evaluation_summary']['metrics_evaluated']:
            best_score = 0
            best_model = None
            for model_key, model_data in data['model_performance'].items():
                if metric in model_data['metrics']:
                    score = model_data['metrics'][metric]['average_score']
                    if score > best_score:
                        best_score = score
                        best_model = f"{model_data['provider'].upper()} {model_data['model']}"
            if best_model:
                best_performers[metric] = (best_model, best_score)
        
        f.write("### Top Performers by Metric\n\n")
        for metric, (model, score) in best_performers.items():
            f.write(f"- **{metric}**: {model} ({score:.3f})\n")
        f.write("\n")
        
        f.write("## Detailed Model Performance\n\n")
        
        for model_key, model_data in data['model_performance'].items():
            provider = model_data['provider'].upper()
            model = model_data['model']
            f.write(f"### {provider} - {model}\n\n")
            f.write(f"**Total Evaluations:** {model_data['total_evaluations']}\n\n")
            
            if model_data['metrics']:
                f.write("| Metric | Average | Min | Max | Std Dev | Median |\n")
                f.write("|--------|---------|-----|-----|---------|--------|\n")
                
                for metric_name, metric_data in model_data['metrics'].items():
                    avg = metric_data['average_score']
                    min_val = metric_data['min_score']
                    max_val = metric_data['max_score']
                    std = metric_data['std_score']
                    median = metric_data['median_score']
                    f.write(f"| {metric_name} | {avg:.3f} | {min_val:.3f} | {max_val:.3f} | {std:.3f} | {median:.3f} |\n")
                f.write("\n")
                
                # Performance rating
                overall_avg = np.mean([m['average_score'] for m in model_data['metrics'].values()])
                if overall_avg > 0.7:
                    rating = "🟢 Excellent"
                elif overall_avg > 0.5:
                    rating = "🟡 Good"
                else:
                    rating = "🔴 Needs Improvement"
                f.write(f"**Overall Performance:** {rating} ({overall_avg:.3f})\n\n")
            else:
                f.write("*No metrics available*\n\n")
    
    print(f"📄 Detailed report saved: {report_file}")

def create_performance_charts(data, output_dir):
    """Create performance comparison charts"""
    
    try:
        # Prepare data for plotting
        models = []
        metrics_data = {}
        
        for model_key, model_data in data['model_performance'].items():
            model_name = f"{model_data['provider'].upper()}\n{model_data['model']}"
            models.append(model_name)
            
            for metric_name, metric_info in model_data['metrics'].items():
                if metric_name not in metrics_data:
                    metrics_data[metric_name] = []
                metrics_data[metric_name].append(metric_info['average_score'])
        
        if not metrics_data:
            print("⚠️ No metrics data available for charts")
            return
        
        # Create comparison chart
        plt.figure(figsize=(14, 10))
        
        # Set up the plot
        x = np.arange(len(models))
        width = 0.8 / len(metrics_data)
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(metrics_data)))
        
        for i, (metric, scores) in enumerate(metrics_data.items()):
            plt.bar(x + i * width, scores, width, label=metric, color=colors[i], alpha=0.8)
        
        plt.xlabel('Models', fontsize=12)
        plt.ylabel('Score', fontsize=12)
        plt.title('Smart ATS FAQ Assistant - Model Performance Comparison', fontsize=14, fontweight='bold')
        plt.xticks(x + width * (len(metrics_data) - 1) / 2, models, rotation=45, ha='right')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_file = os.path.join(output_dir, "model_performance_comparison.png")
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Performance chart saved: {chart_file}")
        
        # Create heatmap
        if len(models) > 1 and len(metrics_data) > 1:
            create_heatmap(models, metrics_data, output_dir)
            
    except Exception as e:
        print(f"⚠️ Could not create charts: {str(e)}")

def create_heatmap(models, metrics_data, output_dir):
    """Create performance heatmap"""
    
    try:
        # Prepare data for heatmap
        heatmap_data = []
        metric_names = list(metrics_data.keys())
        
        for model in models:
            model_scores = []
            for metric in metric_names:
                model_idx = models.index(model)
                if model_idx < len(metrics_data[metric]):
                    model_scores.append(metrics_data[metric][model_idx])
                else:
                    model_scores.append(0)
            heatmap_data.append(model_scores)
        
        # Create heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(heatmap_data, 
                   xticklabels=metric_names,
                   yticklabels=models,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlGn',
                   vmin=0, vmax=1,
                   cbar_kws={'label': 'Score'})
        
        plt.title('Model Performance Heatmap', fontsize=14, fontweight='bold')
        plt.xlabel('Metrics', fontsize=12)
        plt.ylabel('Models', fontsize=12)
        plt.tight_layout()
        
        heatmap_file = os.path.join(output_dir, "model_performance_heatmap.png")
        plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"🔥 Heatmap saved: {heatmap_file}")
        
    except Exception as e:
        print(f"⚠️ Could not create heatmap: {str(e)}")

def print_console_summary(data):
    """Print summary to console"""
    
    print("\n" + "="*80)
    print("📊 SMART ATS FAQ ASSISTANT - MODEL EVALUATION RESULTS")
    print("="*80)
    
    print(f"\n🎯 **Evaluation Summary:**")
    print(f"   • Framework: {data['evaluation_summary']['evaluation_framework']}")
    print(f"   • Models Evaluated: {data['evaluation_summary']['total_models_evaluated']}")
    print(f"   • Metrics: {', '.join(data['evaluation_summary']['metrics_evaluated'])}")
    
    print(f"\n🏆 **Model Performance Rankings:**")
    
    # Calculate overall scores
    model_scores = []
    for model_key, model_data in data['model_performance'].items():
        if model_data['metrics']:
            overall_score = np.mean([m['average_score'] for m in model_data['metrics'].values()])
            model_scores.append((model_key, model_data, overall_score))
    
    # Sort by overall score
    model_scores.sort(key=lambda x: x[2], reverse=True)
    
    for i, (model_key, model_data, overall_score) in enumerate(model_scores, 1):
        provider = model_data['provider'].upper()
        model = model_data['model']
        
        if overall_score > 0.7:
            status = "🥇" if i == 1 else "🟢"
        elif overall_score > 0.5:
            status = "🥈" if i == 2 else "🟡"
        else:
            status = "🥉" if i == 3 else "🔴"
        
        print(f"   {i}. {status} {provider} - {model}: {overall_score:.3f}")
        
        # Show top 3 metrics for this model
        top_metrics = sorted(model_data['metrics'].items(), 
                           key=lambda x: x[1]['average_score'], reverse=True)[:3]
        for metric_name, metric_data in top_metrics:
            score = metric_data['average_score']
            print(f"      • {metric_name}: {score:.3f}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("🚀 Processing RAGAS evaluation results...")
    process_csv_results()
    print("🎉 Comprehensive evaluation report completed!")
