"""
Script to create the complete project folder structure
"""

import os
from pathlib import Path

def create_project_structure():
    """Create all necessary folders and __init__.py files"""
    
    base_dir = Path(__file__).parent
    
    # Define folder structure
    folders = [
        "data-ingestion/api_clients",
        "data-ingestion/producers",
        "data-ingestion/schemas",
        "streaming/flink_jobs",
        "streaming/kafka_utils",
        "ml-models/recommendation",
        "ml-models/churn_prediction",
        "ml-models/demand_forecast",
        "ml-models/models",
        "api/routers",
        "api/models",
        "dashboard/pages",
        "dashboard/utils",
        "database/schemas",
        "tests",
        "scripts",
        "docs",
        "logs"
    ]
    
    # Create folders
    for folder in folders:
        folder_path = base_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {folder}")
        
        # Create __init__.py for Python packages (exclude non-Python folders)
        if folder not in ["logs", "docs", "scripts", "ml-models/models", "database/schemas"]:
            init_file = folder_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"  ✓ Created: {folder}/__init__.py")
    
    # Create .gitkeep for empty folders
    gitkeep_folders = ["logs", "ml-models/models"]
    for folder in gitkeep_folders:
        gitkeep_file = base_dir / folder / ".gitkeep"
        gitkeep_file.touch()
        print(f"✓ Created: {folder}/.gitkeep")
    
    print("\n✅ Folder structure created successfully!")

if __name__ == "__main__":
    create_project_structure()
