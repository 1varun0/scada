import pandas as pd
import matplotlib.pyplot as plt
import os

class Reporter:
    """Generates evaluation reports and visualizations."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_ablation_markdown(self, df_ablation: pd.DataFrame, filename: str = "ablation_results.md"):
        """Save ablation DataFrame as a Markdown table."""
        # Format the dataframe for better readability
        df_display = df_ablation.copy()
        
        # Round floats
        for col in df_display.select_dtypes(include=['float64']).columns:
            df_display[col] = df_display[col].round(4)
            
        md_table = df_display.to_markdown()
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            f.write("# Ablation Study Results\n\n")
            f.write(md_table)
            f.write("\n")
            
        return filepath
        
    def plot_roc_curve(self, y_true, y_scores, title="ROC Curve", filename="roc_curve.png"):
        """Plot and save ROC curve."""
        from sklearn.metrics import roc_curve, auc
        
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title(title)
        plt.legend(loc="lower right")
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath)
        plt.close()
        
        return filepath
