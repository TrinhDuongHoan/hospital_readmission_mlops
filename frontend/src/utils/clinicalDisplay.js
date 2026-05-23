export const fieldLabels = {
  id: "Patient ID",
  race: "Race or Ethnicity",
  gender: "Gender",
  age: "Age Range",
  doctor_full_name: "Assigned Doctor",
  admission_type_id: "Admission Type",
  discharge_disposition_id: "Discharge Status",
  admission_source_id: "Admission Source",
  time_in_hospital: "Length of Stay",
  num_lab_procedures: "Lab Procedures",
  num_procedures: "Non-Lab Procedures",
  num_medications: "Medications",
  number_outpatient: "Outpatient Visits",
  number_emergency: "Emergency Visits",
  number_inpatient: "Inpatient Visits",
  number_diagnoses: "Recorded Diagnoses",
  diag_1: "Primary Diagnosis Code",
  diag_2: "Secondary Diagnosis Code",
  diag_3: "Additional Diagnosis Code",
  max_glu_serum: "Max Glucose Serum",
  A1Cresult: "A1C Result",
  metformin: "Metformin",
  insulin: "Insulin",
  change: "Medication Changed",
  diabetesMed: "Diabetes Medication",
};

export const fieldHelp = {
  admission_type_id: "Numeric source code from the hospital admission dataset.",
  discharge_disposition_id: "Numeric status code captured at discharge.",
  admission_source_id: "Numeric code for where the admission came from.",
  time_in_hospital: "Number of days the patient stayed in hospital.",
  diag_1: "Use ICD-style diagnosis code from the source dataset.",
  diag_2: "Optional secondary ICD-style diagnosis code.",
  diag_3: "Optional additional ICD-style diagnosis code.",
};

const optionLabels = {
  "Unknown/Invalid": "Unknown",
  Ch: "Changed",
  No: "No",
  Yes: "Yes",
  None: "Not tested",
  Norm: "Normal",
};

export function formatFieldLabel(field) {
  return (
    fieldLabels[field] ||
    field.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
}

export function formatOptionLabel(value) {
  return optionLabels[value] || value;
}

export function formatProbability(value) {
  return `${((value || 0) * 100).toFixed(2)}%`;
}

export function getRiskPresentation(level = "low", probability = 0) {
  const normalized = level || (probability >= 0.7 ? "high" : probability >= 0.4 ? "medium" : "low");

  if (normalized === "high") {
    return {
      level: normalized,
      label: "High Priority",
      title: "High readmission risk",
      action: "Review care plan and schedule early follow-up.",
    };
  }

  if (normalized === "medium") {
    return {
      level: normalized,
      label: "Needs Review",
      title: "Moderate readmission risk",
      action: "Check risk factors before discharge.",
    };
  }

  return {
    level: normalized,
    label: "Routine",
    title: "Low readmission risk",
    action: "Continue standard follow-up plan.",
  };
}

export function formatPrediction(prediction) {
  return prediction === 1 ? "Readmission likely" : "Readmission less likely";
}
