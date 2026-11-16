"""
seed_and_train.py - Convenience script to seed initial demonstration records and train models.
"""

from database.db import init_db, bulk_insert_experiments, get_all_experiments, get_experiment_counts
from data.synthetic_data import generate_synthetic_dataset
from ml.train import train_and_compare_models

def main():
    init_db()
    counts = get_experiment_counts()
    print(f"Current DB counts: {counts}")
    if counts["total"] < 50:
        print("Generating 120 synthetic demonstration records...")
        records = generate_synthetic_dataset(n_samples=120, n_participants=18, random_seed=42)
        bulk_insert_experiments(records)
        print("Inserted demo records into SQLite database.")

    df = get_all_experiments(include_synthetic=True)
    print(f"Training models on {len(df)} records...")
    res = train_and_compare_models(df, dataset_label="Synthetic Demonstration Dataset")
    if res.get("success"):
        print(f"Models successfully trained! Best model: {res.get('best_model_name')}")
        for m, data in res["models"].items():
            print(f"  - {m}: RMSE={data['metrics']['RMSE']}s, R2={data['metrics']['R2']}")
    else:
        print(f"Training error: {res.get('error')}")

if __name__ == "__main__":
    main()

