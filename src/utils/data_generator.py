"""
Healthcare Synthetic Data Augmentation
Production-style augmentation script for portfolio project
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid
import os
from pathlib import Path

np.random.seed(42)
random.seed(42)


class HealthcareDataAugmentor:
    def __init__(self, base_data_path: str):
        self.base_data_path = Path(base_data_path)
        self.patients = None
        self.encounters = None
        self.conditions = None

    # ---------------------------------------------------
    # LOAD DATA
    # ---------------------------------------------------
    def load_synthea_data(self):
        print("Loading Synthea CSV files...")

        required_files = ["patients.csv", "encounters.csv", "conditions.csv"]

        for file in required_files:
            if not (self.base_data_path / file).exists():
                raise FileNotFoundError(f"Missing required file: {file}")

        self.patients = pd.read_csv(self.base_data_path / "patients.csv")
        self.encounters = pd.read_csv(self.base_data_path / "encounters.csv")
        self.conditions = pd.read_csv(self.base_data_path / "conditions.csv")

        print(f"✓ Patients:   {len(self.patients):,}")
        print(f"✓ Encounters: {len(self.encounters):,}")
        print(f"✓ Conditions: {len(self.conditions):,}\n")

    # ---------------------------------------------------
    # RARE CONDITIONS
    # ---------------------------------------------------
    def add_rare_conditions(self, n=50):
        print(f"Adding {n} rare condition cases...")

        rare_conditions = [
            {"code": "G20", "description": "Parkinson's disease"},
            {"code": "C50.9", "description": "Breast cancer"},
            {"code": "N18.6", "description": "End-stage renal disease"},
            {"code": "I50.9", "description": "Heart failure"},
            {"code": "Q90.9", "description": "Down syndrome"},
        ]

        new_rows = []

        for _ in range(min(n, len(self.patients))):
            patient_id = random.choice(self.patients["Id"].values)

            patient_encounters = self.encounters[
                self.encounters["PATIENT"] == patient_id
            ]

            if patient_encounters.empty:
                continue

            encounter_id = random.choice(patient_encounters["Id"].values)
            condition = random.choice(rare_conditions)

            new_rows.append({
                "START": datetime.now().strftime("%Y-%m-%d"),
                "STOP": None,
                "PATIENT": patient_id,
                "ENCOUNTER": encounter_id,
                "CODE": condition["code"],
                "DESCRIPTION": condition["description"]
            })

        if new_rows:
            self.conditions = pd.concat(
                [self.conditions, pd.DataFrame(new_rows)],
                ignore_index=True
            )

        print(f"✓ Added {len(new_rows)} rare conditions\n")

    # ---------------------------------------------------
    # DATA QUALITY ISSUES
    # ---------------------------------------------------
    def introduce_data_quality_issues(self):
        print("Injecting data quality issues...")

        # Missing values
        if "REASONDESCRIPTION" in self.encounters.columns:
            n_missing = int(len(self.encounters) * 0.02)
            indices = np.random.choice(self.encounters.index, n_missing, replace=False)
            self.encounters.loc[indices, "REASONDESCRIPTION"] = None
            print(f"✓ Introduced {n_missing} missing values")

        # Duplicate encounters
        n_dup = int(len(self.encounters) * 0.01)
        dup_rows = self.encounters.sample(n_dup).copy()
        dup_rows["Id"] = [str(uuid.uuid4()) for _ in range(len(dup_rows))]
        self.encounters = pd.concat([self.encounters, dup_rows], ignore_index=True)

        print(f"✓ Added {n_dup} duplicate encounters\n")

    # ---------------------------------------------------
    # READMISSIONS
    # ---------------------------------------------------
    def add_readmission_cases(self, n=200):
        print(f"Adding up to {n} readmission cases...")

        if "ENCOUNTERCLASS" not in self.encounters.columns:
            print("⚠ ENCOUNTERCLASS column not found. Skipping readmissions.\n")
            return

        hospital_encounters = self.encounters[
            self.encounters["ENCOUNTERCLASS"].isin(["inpatient", "emergency"])
        ]

        if hospital_encounters.empty:
            print("⚠ No hospital encounters found.\n")
            return

        readmissions = []
        unique_patients = hospital_encounters["PATIENT"].unique()

        for patient_id in unique_patients[:n]:
            patient_data = hospital_encounters[
                hospital_encounters["PATIENT"] == patient_id
            ].sort_values("START")

            first_enc = patient_data.iloc[0]

            try:
                start_date = pd.to_datetime(first_enc["START"])
                readmit_date = start_date + timedelta(days=random.randint(1, 30))

                new_row = first_enc.copy()
                new_row["Id"] = str(uuid.uuid4())
                new_row["START"] = readmit_date.strftime("%Y-%m-%d")
                new_row["REASONDESCRIPTION"] = "Hospital readmission"

                readmissions.append(new_row)

            except Exception:
                continue

        if readmissions:
            self.encounters = pd.concat(
                [self.encounters, pd.DataFrame(readmissions)],
                ignore_index=True
            )

        print(f"✓ Added {len(readmissions)} readmission encounters\n")

    # ---------------------------------------------------
    # SAVE
    # ---------------------------------------------------
    def save(self, output_path):
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        self.patients.to_csv(output_path / "patients.csv", index=False)
        self.encounters.to_csv(output_path / "encounters.csv", index=False)
        self.conditions.to_csv(output_path / "conditions.csv", index=False)

        metadata = {
            "generation_date": datetime.now().isoformat(),
            "total_patients": len(self.patients),
            "total_encounters": len(self.encounters),
            "total_conditions": len(self.conditions),
            "augmentation": True
        }

        pd.DataFrame([metadata]).to_csv(output_path / "metadata.csv", index=False)

        print("✓ Augmented data saved successfully\n")

    # ---------------------------------------------------
    # PIPELINE
    # ---------------------------------------------------
    def run(self, output_path):
        self.load_synthea_data()
        self.add_rare_conditions(50)
        self.introduce_data_quality_issues()
        self.add_readmission_cases(200)
        self.save(output_path)

        print("=" * 60)
        print("AUGMENTATION SUMMARY")
        print("=" * 60)
        print(f"Patients:   {len(self.patients):,}")
        print(f"Encounters: {len(self.encounters):,}")
        print(f"Conditions: {len(self.conditions):,}")
        print("=" * 60)


# ---------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------
if __name__ == "__main__":
    print("\nHEALTHCARE DATA AUGMENTATION PIPELINE\n")

    project_root = Path(__file__).resolve().parents[2]

    base_path = project_root / "data" / "synthetic" / "output" / "csv"
    output_path = project_root / "data" / "synthetic" / "augmented"

    augmentor = HealthcareDataAugmentor(base_path)
    augmentor.run(output_path)